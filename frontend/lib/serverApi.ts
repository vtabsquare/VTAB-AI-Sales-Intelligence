import {cookies} from 'next/headers';
export async function serverGet(path:string){const API=process.env.API_BASE_URL||'http://127.0.0.1:8001';const token=(await cookies()).get('vtab_session')?.value||'';return fetch(`${API}${path}`,{cache:'no-store',headers:token?{authorization:`Bearer ${token}`}:{}})}
