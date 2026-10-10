"""Read-only imports. External text stays unapproved; private Drive links stay inactive."""
import base64
import re
from urllib.parse import urlparse
import httpx
from app.core.config import settings
from app.models.entities import KnowledgeDocument
from app.models.platform import CompanyAsset, ResourceLink
from app.services.knowledge import reindex
from app.services.public_http import public_get


def import_text(db, title, content, category):
    # Changes revoke approval instead of silently replacing approved facts.
    document=db.query(KnowledgeDocument).filter_by(title=title,category=category).first()
    content=content[:40000]
    if document and document.content==content:
        return False
    if not document:
        document=KnowledgeDocument(title=title[:255],category=category,content=content,approved=False)
    else:
        document.content=content;document.approved=False
    db.add(document);db.commit();reindex(db,document)
    return True


def sync_drive(db, client):
    folders=[f.strip() for f in settings.google_drive_folder_ids.split(',') if f.strip()]
    if not all([settings.google_client_id,settings.google_client_secret,settings.google_refresh_token,folders]):
        return {'status':'NOT_CONFIGURED','imported':0}
    if any(not re.fullmatch(r'[\w-]{5,200}', f) for f in folders):
        raise ValueError('Invalid Drive folder ID')
    token_response=client.post('https://oauth2.googleapis.com/token',data={
        'client_id':settings.google_client_id,'client_secret':settings.google_client_secret,
        'refresh_token':settings.google_refresh_token,'grant_type':'refresh_token'})
    token_response.raise_for_status()
    headers={'Authorization':'Bearer '+token_response.json()['access_token']}
    imported=0;files_seen=0;truncated=False
    for folder in folders[:10]:
        page=None
        for _ in range(5):
            params={'q':f"'{folder}' in parents and trashed = false",'pageSize':100,
                    'fields':'nextPageToken,files(id,name,mimeType,webViewLink,description,modifiedTime)',
                    'supportsAllDrives':'true','includeItemsFromAllDrives':'true'}
            if page: params['pageToken']=page
            response=client.get('https://www.googleapis.com/drive/v3/files',headers=headers,params=params)
            response.raise_for_status();data=response.json()
            for file in data.get('files',[]):
                files_seen+=1
                if file.get('mimeType')=='application/vnd.google-apps.folder': continue
                fid=file.get('id','')
                if not re.fullmatch(r'[\w-]{5,200}',fid): continue
                url='https://drive.google.com/file/d/'+fid+'/view'
                resource=db.query(ResourceLink).filter_by(url=url).first()
                if not resource:
                    resource=ResourceLink(title=file.get('name','Drive material')[:255],url=url,
                        resource_type='VIDEO' if file.get('mimeType','').startswith('video/') else 'PRESENTATION',
                        description=(file.get('description') or '')[:4000],tags=['DRIVE','PRIVATE_REVIEW'],active=False)
                    db.add(resource);db.commit();imported+=1
                # Metadata is indexed for owner review; binary slides/video are NOT transcribed.
                import_text(db,('Drive: '+fid)[:255],
                            f"Title: {file.get('name','')}\nDescription: {file.get('description','')}\nMIME type: {file.get('mimeType','')}\nPrivate material: do not send this link until sharing permission is reviewed.",
                            'DRIVE_METADATA')
            page=data.get('nextPageToken')
            if not page: break
        if page: truncated=True
    return {'status':'SYNCED','imported':imported,'files_seen':files_seen,'truncated':truncated,
            'message':'Direct folder children catalogued; slides/video contents need a reviewed text summary. Links remain inactive.'}


def sync_company_sources(db):
    if settings.demo_mode:
        return {'status':'SKIPPED','message':'Company-source network imports require live mode. No external account was accessed.'}
    result={'status':'COMPLETED','drive':{},'documents_changed':0,'issues':[]}
    with httpx.Client(timeout=30,follow_redirects=False) as client:
        try: result['drive']=sync_drive(db,client)
        except Exception:
            db.rollback();result['issues'].append({'source':'Google Drive','message':'Import failed. Check read-only OAuth and folder access.'})
        for asset in db.query(CompanyAsset).filter(CompanyAsset.active.is_(True)).limit(20).all():
            try:
                if asset.asset_type=='COMPANY_WEBSITE':
                    html=public_get(asset.url).text
                    html=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',html,flags=re.I|re.S)
                    from html import unescape
                    content=unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html)))
                    changed=import_text(db,('Website: '+asset.url)[:255],content,'COMPANY_WEBSITE')
                elif asset.asset_type in {'GITHUB_REPOSITORY','GITHUB_REPO'}:
                    url=urlparse(asset.url)
                    parts=url.path.strip('/').split('/')
                    if url.scheme!='https' or url.hostname!='github.com' or len(parts)!=2 or any(not re.fullmatch(r'[\w.-]+',x) for x in parts):
                        raise ValueError('Use an exact https://github.com/owner/repository URL')
                    headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
                    if settings.github_read_token: headers['Authorization']='Bearer '+settings.github_read_token
                    response=client.get('https://api.github.com/repos/'+ '/'.join(parts)+'/readme',headers=headers)
                    response.raise_for_status();readme=response.json()
                    if readme.get('encoding')!='base64' or readme.get('size',0)>200000:
                        raise ValueError('README encoding or size not supported')
                    content=base64.b64decode(readme['content']).decode('utf-8')
                    changed=import_text(db,('GitHub: '+ '/'.join(parts))[:255],content,'GITHUB_README')
                else: continue
                result['documents_changed']+=int(changed)
            except Exception:
                db.rollback();result['issues'].append({'source':asset.name,'message':'Read-only import failed; verify URL and access.'})
    if result['issues']: result['status']='PARTIAL'
    return result
