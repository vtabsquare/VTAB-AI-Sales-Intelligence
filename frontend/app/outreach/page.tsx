"use client";
import {apiFetch, apiJson, reportApiError} from "../../lib/api";








import { useEffect, useState } from "react";











/* ============================================================



   TYPES



   ============================================================ */







type Recipient = {



  name?: string | null;



  title?: string | null;



  email?: string | null;







  source?: string | null;







  verification?: string | null;







  verified?: boolean;







  do_not_contact?: boolean;



};











type Opportunity = {



  title?: string | null;



  country?: string | null;



};













type ConfirmationModal =

  | {

      kind: "test-verify";

      item: Outreach;

    }

  | {

      kind: "send";

      item: Outreach;

    }

  | null;





type Outreach = {



  id: string;







  opportunity_id: string;







  contact_id?: string | null;







  subject: string;







  body_text: string;







  status: string;







  created_at?: string | null;







  human_approved?: boolean;







  send_allowed?: boolean;







  recipient?: Recipient | null;







  opportunity?: Opportunity | null;











  /* ----------------------------------------------------------



     Compatibility with backend flat recipient fields



     ---------------------------------------------------------- */







  recipient_name?: string | null;







  recipient_title?: string | null;







  recipient_email?: string | null;







  recipient_source?: string | null;







  recipient_verified?: boolean;



};











type ManualRecipientForm = {



  name: string;



  title: string;



  email: string;



};











/* ============================================================



   API



   ============================================================ */







const API = "/backend-api";











/* ============================================================



   COMPONENT



   ============================================================ */







export default function OutreachSendCenter() {











  /* ==========================================================



     STATE



     ========================================================== */







  const [items, setItems] =



    useState<Outreach[]>([]);











  const [loading, setLoading] =



    useState(true);











  const [sending, setSending] =



    useState<string | null>(null);











  const [resolving, setResolving] =



    useState<string | null>(null);





  const [verifying, setVerifying] =



    useState<string | null>(null);







  const [confirmationModal, setConfirmationModal] =

    useState<ConfirmationModal>(null);











  const [savingRecipient, setSavingRecipient] =



    useState<string | null>(null);











  const [message, setMessage] =



    useState("");











  const [messageType, setMessageType] =



    useState<



      "success" |



      "error" |



      "info"



    >("info");











  const [manualEntryId, setManualEntryId] =



    useState<string | null>(null);











  const [manualForm, setManualForm] =



    useState<ManualRecipientForm>({



      name: "",



      title: "",



      email: "",



    });











  /* ==========================================================



     MESSAGE HELPER



     ========================================================== */







  function showMessage(



    text: string,



    type:



      | "success"



      | "error"



      | "info"



      = "info"



  ) {







    setMessage(text);







    setMessageType(type);



  }











  function clearMessage() {







    setMessage("");



  }











  /* ==========================================================



     NORMALIZE RECIPIENT







     The backend currently supports both:







     recipient: {...}







     and flat fields:







     recipient_name



     recipient_email



     recipient_verified







     This helper makes the frontend support both.



     ========================================================== */







  function getRecipient(



    item: Outreach



  ): Recipient {







    return {







      name:



        item.recipient?.name ??



        item.recipient_name ??



        null,











      title:



        item.recipient?.title ??



        item.recipient_title ??



        null,











      email:



        item.recipient?.email ??



        item.recipient_email ??



        null,











      source:



        item.recipient?.source ??



        item.recipient_source ??



        null,











      verification:



        item.recipient?.verification ??



        null,











      verified:



        item.recipient?.verified ??



        item.recipient_verified ??



        false,











      do_not_contact:



        item.recipient?.do_not_contact ??



        false,



    };



  }











  /* ==========================================================



     UPDATE ONE RECIPIENT LOCALLY



     ========================================================== */







  function updateRecipientInState(



    outreachId: string,



    recipient: Recipient,



    contactId?: string | null



  ) {







    setItems(



      (current) =>



        current.map(



          (item) => {







            if (



              item.id !== outreachId



            ) {







              return item;



            }











            const verified =



              recipient.verified === true;











            const hasEmail =



              Boolean(



                recipient.email



              );











            const blocked =



              recipient.do_not_contact === true;











            return {







              ...item,











              contact_id:



                contactId ??



                item.contact_id,











              recipient,











              recipient_name:



                recipient.name ??



                null,











              recipient_title:



                recipient.title ??



                null,











              recipient_email:



                recipient.email ??



                null,











              recipient_source:



                recipient.source ??



                null,











              recipient_verified:



                verified,











              send_allowed:



                item.status === "APPROVED" &&



                hasEmail &&



                verified &&



                !blocked,



            };



          }



        )



    );



  }











  /* ==========================================================



     LOAD SEND CENTER



     ========================================================== */







  async function load() {







    try {







      setLoading(true);











      const response =



        await apiFetch(



          `${API}/outreach/send-center`,



          {



            cache: "no-store",



          }



        );











      if (!response.ok) {







        throw new Error(



          "Unable to load approved outreach."



        );



      }











      const data =



        await response.json();











      setItems(



        Array.isArray(data)



          ? data



          : []



      );

      clearMessage();











    } catch (error: any) {







      showMessage(



        error?.message ||



        "Unable to load approved outreach.",



        "error"



      );











    } finally {







      setLoading(false);



    }



  }











  /* ==========================================================



     INITIAL LOAD



     ========================================================== */







  useEffect(



    () => {







      load();







    },



    []



  );











  /* ==========================================================



     FIND / RESOLVE RECIPIENT



     ========================================================== */







  async function resolveRecipient(



    item: Outreach



  ) {







    try {







      setResolving(



        item.id



      );











      clearMessage();











      const response =



        await apiFetch(



          `${API}/outreach/${item.id}/resolve-recipient`,



          {



            method: "POST",







            headers: {



              "Content-Type":



                "application/json",



            },



          }



        );











      const data =



        await response.json();











      if (!response.ok) {







        throw new Error(



          data?.detail ||



          "Unable to find recipient."



        );



      }











      /* ------------------------------------------------------



         No recipient found



         ------------------------------------------------------ */







      if (!data.resolved) {







        showMessage(



          data?.message ||



          (



            "No existing recipient was found. " +



            "You can enter the recipient manually."



          ),



          "info"



        );











        setManualForm({



          name: "",



          title: "",



          email: "",



        });











        setManualEntryId(



          item.id



        );











        return;



      }











      /* ------------------------------------------------------



         Recipient found



         ------------------------------------------------------ */







      const recipient: Recipient = {







        name:



          data.name ??



          null,











        title:



          data.title ??



          null,











        email:



          data.email ??



          null,











        source:



          data.source ??



          null,











        verification:



          data.verification ??



          null,











        verified:



          data.verified === true,











        do_not_contact:



          data.do_not_contact === true,



      };











      updateRecipientInState(



        item.id,



        recipient,



        data.contact_id



      );











      setManualEntryId(



        null



      );











      if (



        data.do_not_contact === true



      ) {







        showMessage(



          "Recipient found, but the contact is marked Do Not Contact.",



          "error"



        );







        return;



      }











      if (



        data.verified === true



      ) {







        showMessage(



          `Recipient found and verified: ${data.email}`,



          "success"



        );







      } else {







        showMessage(



          (



            `Recipient found: ${data.email}. ` +



            "The email address still requires verification before sending."



          ),



          "info"



        );



      }











    } catch (error: any) {







      showMessage(



        error?.message ||



        "Unable to find recipient.",



        "error"



      );











    } finally {







      setResolving(



        null



      );



    }



  }











  /* ==========================================================



     OPEN MANUAL RECIPIENT FORM



     ========================================================== */







  function openManualRecipient(



    item: Outreach



  ) {







    const recipient =



      getRecipient(item);











    setManualForm({







      name:



        recipient.name ||



        "",











      title:



        recipient.title ||



        "",











      email:



        recipient.email ||



        "",



    });











    setManualEntryId(



      item.id



    );











    clearMessage();



  }











  /* ==========================================================



     CANCEL MANUAL RECIPIENT



     ========================================================== */







  function cancelManualRecipient() {







    setManualEntryId(



      null



    );











    setManualForm({



      name: "",



      title: "",



      email: "",



    });



  }











  /* ==========================================================



     SAVE MANUAL RECIPIENT



     ========================================================== */







  async function saveManualRecipient(



    item: Outreach



  ) {







    const email =



      manualForm.email.trim();











    if (!email) {







      showMessage(



        "Recipient email address is required.",



        "error"



      );







      return;



    }











    try {







      setSavingRecipient(



        item.id



      );











      clearMessage();











      const response =



        await apiFetch(



          `${API}/outreach/${item.id}/recipient`,



          {



            method: "PATCH",







            headers: {



              "Content-Type":



                "application/json",



            },







            body:



              JSON.stringify({







                name:



                  manualForm.name.trim()



                    ? manualForm.name.trim()



                    : null,











                title:



                  manualForm.title.trim()



                    ? manualForm.title.trim()



                    : null,











                email,











                source:



                  "MANUAL",











                confidence:



                  100,



              }),



          }



        );











      const data =



        await response.json();











      if (!response.ok) {







        throw new Error(



          data?.detail ||



          "Unable to save recipient."



        );



      }











      const recipient: Recipient = {







        name:



          data?.recipient?.name ??



          manualForm.name ??



          null,











        title:



          data?.recipient?.title ??



          manualForm.title ??



          null,











        email:



          data?.recipient?.email ??



          email,











        source:



          data?.recipient?.source ??



          "MANUAL",











        verification:



          data?.recipient?.verification ??



          "MANUAL_REVIEW",











        verified:



          data?.recipient?.verified === true,











        do_not_contact:



          data?.recipient?.do_not_contact === true,



      };











      updateRecipientInState(



        item.id,



        recipient,



        data?.contact_id



      );











      setManualEntryId(



        null



      );











      setManualForm({



        name: "",



        title: "",



        email: "",



      });











      showMessage(



        data?.message ||



        (



          "Recipient saved successfully. " +



          "Email verification is required before sending."



        ),



        "success"



      );











      /*



       * Reload from backend so UI always reflects



       * the database version.



       */







      await load();











    } catch (error: any) {







      showMessage(



        error?.message ||



        "Unable to save recipient.",



        "error"



      );











    } finally {







      setSavingRecipient(



        null



      );



    }



  }











  /* ==========================================================



     VERIFY RECIPIENT EMAIL



     ========================================================== */



  async function confirmRecipientEvidence(item:Outreach){
    const evidence=window.prompt('Describe the official source or prior correspondence you reviewed to confirm this recipient. Do not enter secrets.');
    if(!evidence)return;
    if(!window.confirm('Confirm that you personally reviewed this recipient evidence? This does not prove mailbox delivery.'))return;
    setVerifying(item.id);
    try{await apiJson(`/outreach/${item.id}/confirm-recipient-evidence`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({evidence,confirmed:true})});await load();}catch(error){reportApiError(error)}finally{setVerifying(null)}
  }

  async function verifyRecipient(

    item: Outreach

  ) {

    try {

      setVerifying(item.id);

      clearMessage();



      const response = await apiFetch(

        `${API}/outreach/${item.id}/verify-recipient`,

        {

          method: "POST",

          headers: {

            "Content-Type": "application/json",

          },

        }

      );



      const data = await response.json();



      if (!response.ok) {

        throw new Error(

          data?.detail ||

          "Unable to verify recipient email."

        );

      }



      const current = getRecipient(item);

      const verification =

        data?.verification ??

        data?.status ??

        current.verification ??

        null;



      const isVerified =

        data?.verified === true ||

        verification === "VERIFIED" ||

        verification === "TEST_VERIFIED";



      updateRecipientInState(

        item.id,

        {

          ...current,

          email: data?.email ?? current.email,

          verification,

          verified: isVerified,

          do_not_contact:

            data?.do_not_contact ??

            current.do_not_contact ??

            false,

        },

        data?.contact_id ?? item.contact_id

      );



      if (isVerified) {

        showMessage(

          data?.message ||

          "Recipient email verified successfully.",

          "success"

        );

      } else {

        showMessage(

          data?.message ||

          `Verification completed with status: ${verification || "REVIEW_REQUIRED"}. Sending remains blocked until the recipient is verified.`,

          "info"

        );

      }



      await load();

    } catch (error: any) {

      showMessage(

        error?.message ||

        "Unable to verify recipient email.",

        "error"

      );

    } finally {

      setVerifying(null);

    }

  }





  /* ==========================================================



     TEST-ONLY RECIPIENT VERIFICATION



     Local development only. Backend enforces APP_ENV.



     ========================================================== */



  function testVerifyRecipient(

    item: Outreach

  ) {

    const recipient = getRecipient(item);



    if (!recipient.email) {

      showMessage(

        "Identify a recipient email before using test verification.",

        "error"

      );

      return;

    }



    setConfirmationModal({

      kind: "test-verify",

      item,

    });

  }





  async function confirmTestVerification() {

    if (

      !confirmationModal ||

      confirmationModal.kind !== "test-verify"

    ) {

      return;

    }



    const item = confirmationModal.item;

    const recipient = getRecipient(item);



    if (!recipient.email) {

      setConfirmationModal(null);

      showMessage(

        "Identify a recipient email before using test verification.",

        "error"

      );

      return;

    }



    try {

      setVerifying(item.id);

      clearMessage();



      const response = await apiFetch(

        `${API}/outreach/${item.id}/test-verify-recipient`,

        {

          method: "POST",

          headers: {

            "Content-Type": "application/json",

          },

        }

      );



      const data = await response.json();



      if (!response.ok) {

        throw new Error(

          data?.detail ||

          "Unable to apply test verification."

        );

      }



      const current = getRecipient(item);



      updateRecipientInState(

        item.id,

        {

          ...current,

          email: data?.email ?? current.email,

          verification: "TEST_VERIFIED",

          verified: true,

          do_not_contact:

            data?.do_not_contact ??

            current.do_not_contact ??

            false,

        },

        data?.contact_id ?? item.contact_id

      );



      setConfirmationModal(null);



      showMessage(

        data?.message ||

        "Recipient marked TEST_VERIFIED for local development.",

        "success"

      );



      await load();

    } catch (error: any) {

      showMessage(

        error?.message ||

        "Unable to apply test verification.",

        "error"

      );

    } finally {

      setVerifying(null);

    }

  }





  /* ==========================================================



     SEND OUTREACH



     ========================================================== */







  function sendOutreach(

    item: Outreach

  ) {

    const recipient = getRecipient(item);



    if (!recipient.email) {

      showMessage(

        "This outreach cannot be sent because no recipient email is available.",

        "error"

      );

      return;

    }



    if (recipient.do_not_contact) {

      showMessage(

        "This outreach cannot be sent because the recipient is marked Do Not Contact.",

        "error"

      );

      return;

    }



    if (recipient.verified !== true) {

      showMessage(

        "This outreach cannot be sent yet. The recipient email must be verified first.",

        "error"

      );

      return;

    }



    setConfirmationModal({

      kind: "send",

      item,

    });

  }





  async function confirmSendOutreach() {

    if (

      !confirmationModal ||

      confirmationModal.kind !== "send"

    ) {

      return;

    }



    const item = confirmationModal.item;

    const recipient = getRecipient(item);



    if (!recipient.email) {

      setConfirmationModal(null);

      showMessage(

        "This outreach cannot be sent because no recipient email is available.",

        "error"

      );

      return;

    }



    try {

      setSending(item.id);

      clearMessage();



      const response = await apiFetch(

        `${API}/outreach/${item.id}/send`,

        {

          method: "POST",
            body: JSON.stringify({confirmed:true}),

          headers: {

            "Content-Type": "application/json",

          },

        }

      );



      const data = await response.json();



      if (!response.ok) {

        throw new Error(

          data?.detail ||

          "Unable to send outreach."

        );

      }



      setConfirmationModal(null);



      const deliveryStatus =

        data?.status === "SIMULATED_SENT"

          ? "simulated successfully"

          : data?.status === "GRAPH_ACCEPTED"

            ? "accepted by Microsoft Graph"

            : "processed successfully";



      showMessage(

        data?.message ||

        `Outreach ${deliveryStatus} for ${recipient.email}.`,

        "success"

      );



      await load();

    } catch (error: any) {

      showMessage(

        error?.message ||

        "Unable to send outreach.",

        "error"

      );

    } finally {

      setSending(null);

    }

  }





  /* ==========================================================



     LOADING SCREEN



     ========================================================== */







  if (loading) {







    return (







      <div className="vt-send-page">







        <div className="panel">







          Loading approved outreach...







        </div>







      </div>



    );



  }











  /* ==========================================================



     COUNTERS



     ========================================================== */







  const recipientCount =



    items.filter(



      (item) =>



        Boolean(



          getRecipient(item).email



        )



    ).length;











  const readyCount =



    items.filter(



      (item) => {







        const recipient =



          getRecipient(item);











        return (



          item.status === "APPROVED" &&



          Boolean(



            recipient.email



          ) &&



          recipient.verified === true &&



          recipient.do_not_contact !== true



        );



      }



    ).length;











  /* ==========================================================



     PAGE



     ========================================================== */







  return (







    <div className="vt-send-page">











      {/* ======================================================



          HEADER



          ====================================================== */}







      <div className="vt-send-hero">











        <div>







          <div className="eyebrow">







            ✦ CONTROLLED OUTBOUND COMMUNICATION







          </div>











          <h1>



            Send Center



          </h1>











          <p className="muted">







            Review approved outreach,



            identify and verify the recipient,



            and send communication under



            human control.







          </p>







        </div>











        <div className="vt-ready-pill">







          ◎ {readyCount} Ready to Send







        </div>











      </div>











      {/* ======================================================



          STATUS CARDS



          ====================================================== */}







      <div className="vt-kpi-grid">











        {/* ----------------------------------------------------



            APPROVAL



            ---------------------------------------------------- */}







        <div className="vt-kpi-card">







          <div className="vt-kpi-icon">
            ✅
          </div>











          <div>







            <span>



              APPROVAL STATUS



            </span>







            <strong>



              Approved



            </strong>







            <small>



              Human reviewed



            </small>







          </div>







        </div>











        {/* ----------------------------------------------------



            RECIPIENTS



            ---------------------------------------------------- */}







        <div className="vt-kpi-card">







          <div className="vt-kpi-icon">
            👥
          </div>











          <div>







            <span>



              RECIPIENTS FOUND



            </span>







            <strong>







              {recipientCount}







            </strong>







            <small>







              Of {items.length} approved







            </small>







          </div>







        </div>











        {/* ----------------------------------------------------



            READY



            ---------------------------------------------------- */}







        <div className="vt-kpi-card">







          <div className="vt-kpi-icon">
            ✉️
          </div>











          <div>







            <span>



              READY TO SEND



            </span>







            <strong>







              {readyCount}







            </strong>







            <small>



              Verified recipients



            </small>







          </div>







        </div>











        {/* ----------------------------------------------------



            CONTROL



            ---------------------------------------------------- */}







        <div className="vt-kpi-card">







          <div className="vt-kpi-icon">
            🛡️
          </div>











          <div>







            <span>



              SEND CONTROL



            </span>







            <strong>



              Protected



            </strong>







            <small>



              Manual confirmation required



            </small>







          </div>







        </div>











      </div>











      {/* ======================================================



          MESSAGE



          ====================================================== */}







      {message && (







        <div



          className={



            `send-message ${messageType}`



          }



        >







          <span>



            {message}



          </span>











          <button



            type="button"



            className="send-message-close"



            onClick={



              clearMessage



            }



            aria-label="Close message"



          >







            ×







          </button>







        </div>



      )}











      {/* ======================================================



          EMPTY STATE



          ====================================================== */}







      {!items.length && (







        <div className="send-empty">











          <div className="send-empty-icon">







            ✓







          </div>











          <h2>







            No approved outreach waiting







          </h2>











          <p>







            Messages will appear here



            after they have completed



            human approval.







          </p>











        </div>



      )}











      {/* ======================================================



          APPROVED MESSAGES



          ====================================================== */}







      {items.map(



        (item, index) => {











          const recipient =



            getRecipient(item);











          const hasEmail =



            Boolean(



              recipient.email



            );











          const verified =



            recipient.verified === true;











          const doNotContact =



            recipient.do_not_contact === true;











          const readyToSend =



            item.status === "APPROVED" &&



            hasEmail &&



            verified &&



            !doNotContact;











          const editingRecipient =



            manualEntryId === item.id;











          const isResolving =



            resolving === item.id;











          const isSaving =



            savingRecipient === item.id;











          const isSending =



            sending === item.id;











          return (







            <div



              className="send-card"



              key={item.id}



            >











              {/* ==============================================



                  CARD HEADER



                  ============================================== */}







              <div className="send-card-header">











                <div>











                  <div className="send-card-label">







                    APPROVED OUTREACH #{index + 1}







                  </div>











                  <h2>







                    {item.subject}







                  </h2>











                </div>











                <div className="approved-pill">







                  ✓ APPROVED







                </div>











              </div>











              {/* ==============================================



                  META



                  ============================================== */}







              <div className="send-meta">











                <span>







                  Opportunity







                  <strong>







                    {item.opportunity_id



                      ? `${item.opportunity_id.slice(



                          0,



                          10



                        )}...`



                      : "—"}







                  </strong>







                </span>











                <span>







                  Draft







                  <strong>







                    {item.id



                      ? `${item.id.slice(



                          0,



                          10



                        )}...`



                      : "—"}







                  </strong>







                </span>











                <span className="human-approved">







                  ✓ Human Approved







                </span>











              </div>











              {/* ==============================================



                  CONTENT



                  ============================================== */}







              <div className="send-content">











                {/* ============================================



                    RECIPIENT TITLE



                    ============================================ */}







                <div className="recipient-section-header">











                  <div className="send-section-title">







                    ◎ RECIPIENT







                  </div>











                  {hasEmail &&



                   !editingRecipient && (







                    <button



                      type="button"



                      className="recipient-edit-button"



                      onClick={() =>



                        openManualRecipient(



                          item



                        )



                      }



                    >







                      Edit Recipient







                    </button>







                  )}











                </div>











                {/* ============================================



                    RECIPIENT FOUND



                    ============================================ */}







                {hasEmail &&



                 !editingRecipient && (







                  <div



                    className={



                      verified



                        ? "recipient-card recipient-card-verified"



                        : "recipient-card"



                    }



                  >











                    <div className="recipient-avatar">







                      {recipient.name



                        ?.charAt(0)



                        ?.toUpperCase() ||



                        "?"}







                    </div>











                    <div className="recipient-details">











                      <strong>







                        {recipient.name ||



                          "Business Contact"}







                      </strong>











                      {recipient.title && (







                        <span>







                          {recipient.title}







                        </span>







                      )}











                      <span className="recipient-email">







                        {recipient.email}







                      </span>











                      {recipient.source && (







                        <small className="recipient-source">







                          Source:{" "}



                          {recipient.source}







                        </small>







                      )}











                    </div>











                    {/* ----------------------------------------

                        STATUS / VERIFICATION ACTIONS

                        ---------------------------------------- */}



                    <div className="recipient-verification-actions">

                      {doNotContact ? (

                        <div className="verification-pill blocked">

                          DO NOT CONTACT

                        </div>

                      ) : verified ? (

                        <div className="verification-pill verified">

                          {recipient.verification === "TEST_VERIFIED"

                            ? "✓ TEST VERIFIED"

                            : "✓ VERIFIED"}

                        </div>

                      ) : (

                        <>

                          <div className="verification-pill warning">

                            {recipient.verification ||

                              "VERIFICATION REQUIRED"}

                          </div>



                          <button

                            type="button"

                            className="verify-email-button"

                            disabled={verifying === item.id}

                            onClick={() => verifyRecipient(item)}

                          >

                            {verifying === item.id

                              ? "Verifying..."

                              : "✓ Verify Email"}

                          </button>



                          <button

                            type="button"

                            className="test-verify-button"

                            disabled={verifying === item.id}

                            onClick={() => testVerifyRecipient(item)}

                          >

                            Test Verify

                          </button>
                          <button type="button" disabled={verifying===item.id} onClick={()=>void confirmRecipientEvidence(item)}>Confirm recipient evidence</button>

                        </>

                      )}

                    </div>



                  </div>

                )}





                {/* ============================================



                    RECIPIENT MISSING



                    ============================================ */}







                {!hasEmail &&



                 !editingRecipient && (







                  <div className="recipient-card recipient-missing-card">











                    <div className="recipient-avatar">







                      ?







                    </div>











                    <div className="recipient-details">











                      <strong>







                        Recipient not identified







                      </strong>











                      <span>







                        Email address unavailable







                      </span>











                    </div>











                    <div className="recipient-action-group">











                      <button



                        type="button"



                        className="find-recipient-button"



                        disabled={



                          isResolving



                        }



                        onClick={() =>



                          resolveRecipient(



                            item



                          )



                        }



                      >







                        {isResolving



                          ? "Searching..."



                          : "◎ Find Recipient"}







                      </button>











                      <button



                        type="button"



                        className="manual-recipient-button"



                        disabled={



                          isResolving



                        }



                        onClick={() =>



                          openManualRecipient(



                            item



                          )



                        }



                      >







                        + Enter Manually







                      </button>











                    </div>











                  </div>







                )}











                {/* ============================================



                    MANUAL RECIPIENT FORM



                    ============================================ */}







                {editingRecipient && (







                  <div className="recipient-manual-form">











                    <div className="recipient-form-heading">











                      <div>







                        <strong>







                          Recipient Details







                        </strong>











                        <span>







                          Enter the business



                          contact information.







                        </span>







                      </div>











                    </div>











                    {/* ----------------------------------------



                        NAME / TITLE



                        ---------------------------------------- */}







                    <div className="recipient-form-grid">











                      <div className="recipient-form-field">











                        <label>







                          Contact Name







                        </label>











                        <input



                          type="text"



                          placeholder="e.g. John Smith"



                          value={



                            manualForm.name



                          }



                          onChange={



                            (event) =>



                              setManualForm({



                                ...manualForm,







                                name:



                                  event.target.value,



                              })



                          }



                        />











                      </div>











                      <div className="recipient-form-field">











                        <label>







                          Job Title







                        </label>











                        <input



                          type="text"



                          placeholder="e.g. Head of Data"



                          value={



                            manualForm.title



                          }



                          onChange={



                            (event) =>



                              setManualForm({



                                ...manualForm,







                                title:



                                  event.target.value,



                              })



                          }



                        />











                      </div>











                      {/* --------------------------------------



                          EMAIL



                          -------------------------------------- */}







                      <div



                        className={



                          "recipient-form-field " +



                          "recipient-form-email"



                        }



                      >











                        <label>







                          Business Email *







                        </label>











                        <input



                          type="email"



                          placeholder="name@company.com"



                          value={



                            manualForm.email



                          }



                          onChange={



                            (event) =>



                              setManualForm({



                                ...manualForm,







                                email:



                                  event.target.value,



                              })



                          }



                        />











                      </div>











                    </div>











                    {/* ----------------------------------------



                        VERIFICATION NOTE



                        ---------------------------------------- */}







                    <div className="recipient-verification-note">











                      <strong>







                        ⚠ Email verification required







                      </strong>











                      <span>







                        Manually entering an email



                        address does not automatically



                        verify the mailbox. Sending



                        remains blocked until the



                        address has been verified.







                      </span>











                    </div>











                    {/* ----------------------------------------



                        FORM ACTIONS



                        ---------------------------------------- */}







                    <div className="recipient-form-actions">











                      <button



                        type="button"



                        className="recipient-cancel-button"



                        disabled={



                          isSaving



                        }



                        onClick={



                          cancelManualRecipient



                        }



                      >







                        Cancel







                      </button>











                      <button



                        type="button"



                        className="recipient-save-button"



                        disabled={



                          isSaving ||



                          !manualForm.email.trim()



                        }



                        onClick={() =>



                          saveManualRecipient(



                            item



                          )



                        }



                      >







                        {isSaving



                          ? "Saving..."



                          : "Save Recipient"}







                      </button>











                    </div>











                  </div>







                )}











                {/* ============================================



                    EMAIL PREVIEW



                    ============================================ */}







                <div className="send-section-title email-heading">







                  ✉ EMAIL PREVIEW







                </div>











                <div className="send-email-preview">











                  <div className="send-email-subject">











                    <span>







                      To:







                    </span>











                    <strong>







                      {recipient.email ||



                        "Recipient email required"}







                    </strong>











                  </div>











                  <div className="send-email-subject">











                    <span>







                      Subject:







                    </span>











                    <strong>







                      {item.subject}







                    </strong>











                  </div>











                  <pre className="send-email-body">







                    {item.body_text}







                  </pre>











                </div>











                {/* ============================================



                    SEND READINESS



                    ============================================ */}







                {doNotContact ? (







                  <div className="send-warning send-warning-blocked">











                    <div className="send-warning-icon">







                      !







                    </div>











                    <div>











                      <strong>







                        Sending blocked







                      </strong>











                      <p>







                        This recipient is marked



                        Do Not Contact. No outbound



                        communication can be sent.







                      </p>











                    </div>











                  </div>







                ) : !hasEmail ? (







                  <div className="send-warning">











                    <div className="send-warning-icon">







                      !







                    </div>











                    <div>











                      <strong>







                        Recipient required







                      </strong>











                      <p>







                        Identify the recipient before



                        sending this approved outreach.







                      </p>











                    </div>











                  </div>







                ) : !verified ? (







                  <div className="send-warning">











                    <div className="send-warning-icon">







                      !







                    </div>











                    <div>











                      <strong>







                        Email verification required







                      </strong>











                      <p>







                        The recipient has been identified,



                        but the email address must be



                        verified before sending.







                      </p>











                    </div>











                  </div>







                ) : (







                  <div className="send-warning send-warning-ready">











                    <div className="send-warning-icon">







                      ✓







                    </div>











                    <div>











                      <strong>







                        Ready for final human confirmation







                      </strong>











                      <p>







                        The outreach is approved and the



                        recipient email is verified.



                        Sending still requires your final



                        confirmation.







                      </p>











                    </div>











                  </div>







                )}











                {/* ============================================



                    ACTIONS



                    ============================================ */}







                <div className="send-actions">











                  <button



                    type="button"



                    className="send-button"



                    disabled={



                      isSending ||



                      !readyToSend



                    }



                    onClick={() =>



                      sendOutreach(



                        item



                      )



                    }



                  >







                    {isSending



                      ? "Sending..."



                      : readyToSend



                        ? "✉ Send Approved Outreach"



                        : "✉ Send Not Available"}







                  </button>











                </div>











              </div>











              {/* ==============================================



                  FOOTER



                  ============================================== */}







              <div className="send-card-footer">











                <span>







                  <span className="approved-dot" />







                  Approved for outbound communication







                </span>











                <span>







                  Human-controlled sending







                </span>











              </div>











            </div>







          );



        }



      )}









      {/* ======================================================

          PREMIUM HUMAN-CONTROL CONFIRMATION MODAL

          ====================================================== */}



      {confirmationModal && (() => {

        const modalItem = confirmationModal.item;

        const modalRecipient = getRecipient(modalItem);

        const isTestVerification =

          confirmationModal.kind === "test-verify";

        const isBusy =

          verifying === modalItem.id ||

          sending === modalItem.id;



        return (

          <div

            className="vtab-modal-backdrop"

            role="presentation"

            onMouseDown={(event) => {

              if (

                event.target === event.currentTarget &&

                !isBusy

              ) {

                setConfirmationModal(null);

              }

            }}

          >

            <section

              className="vtab-confirm-modal"

              role="dialog"

              aria-modal="true"

              aria-labelledby="vtab-confirm-title"

            >

              <div

                className={

                  isTestVerification

                    ? "vtab-modal-icon vtab-modal-icon-warning"

                    : "vtab-modal-icon vtab-modal-icon-send"

                }

              >

                {isTestVerification ? "⚗" : "✉"}

              </div>



              <div className="vtab-modal-heading">

                <div className="vtab-modal-eyebrow">

                  {isTestVerification

                    ? "LOCAL DEVELOPMENT CONTROL"

                    : "SECURE OUTBOUND COMMUNICATION"}

                </div>



                <h2 id="vtab-confirm-title">

                  {isTestVerification

                    ? "Confirm Test Verification"

                    : "Confirm Approved Outreach"}

                </h2>



                <p>

                  {isTestVerification

                    ? "This development-only action marks the address TEST_VERIFIED. It does not prove that the real mailbox exists."

                    : "Review the final recipient and message details before allowing the backend to perform its safety checks and send."}

                </p>

              </div>



              <div className="vtab-modal-summary">

                {!isTestVerification && (

                  <div className="vtab-modal-summary-row">

                    <span>From</span>

                    <strong>

                      Microsoft 365 configured sender

                    </strong>

                  </div>

                )}



                <div className="vtab-modal-summary-row">

                  <span>To</span>

                  <strong>

                    {modalRecipient.email || "No recipient"}

                  </strong>

                </div>



                {!isTestVerification && (

                  <div className="vtab-modal-summary-row">

                    <span>Subject</span>

                    <strong>{modalItem.subject}</strong>

                  </div>

                )}



                <div className="vtab-modal-summary-row">

                  <span>Verification</span>

                  <strong>

                    {isTestVerification

                      ? modalRecipient.verification || "NOT VERIFIED"

                      : modalRecipient.verification || "VERIFIED"}

                  </strong>

                </div>

              </div>



              <div

                className={

                  isTestVerification

                    ? "vtab-modal-notice warning"

                    : "vtab-modal-notice success"

                }

              >

                <span>

                  {isTestVerification ? "!" : "✓"}

                </span>

                <div>

                  <strong>

                    {isTestVerification

                      ? "Development bypass only"

                      : "Human-controlled send"}

                  </strong>

                  <p>

                    {isTestVerification

                      ? "Live sends reject TEST_VERIFIED recipients, including development mode."

                      : "The backend will re-check approval, suppression, recipient email and verification before delivery."}

                  </p>

                </div>

              </div>



              <div className="vtab-modal-actions">

                <button

                  type="button"

                  className="vtab-modal-cancel"

                  disabled={isBusy}

                  onClick={() => setConfirmationModal(null)}

                >

                  Cancel

                </button>



                <button

                  type="button"

                  className={

                    isTestVerification

                      ? "vtab-modal-confirm warning"

                      : "vtab-modal-confirm send"

                  }

                  disabled={isBusy}

                  onClick={

                    isTestVerification

                      ? confirmTestVerification

                      : confirmSendOutreach

                  }

                >

                  {isBusy

                    ? isTestVerification

                      ? "Verifying..."

                      : "Sending..."

                    : isTestVerification

                      ? "Confirm Test Verification"

                      : "Confirm & Send"}

                </button>

              </div>

            </section>

          </div>

        );

      })()}









    </div>



  );



}