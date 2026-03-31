<scratchpad>
The user wants a chronological list of medical visits. I need to go through the document and extract relevant information for each valid medical encounter.

Here's my plan:
1.  **Iterate through the document** section by section.
2.  **Identify potential medical encounters.** This includes "Provider Note", "Specialist Consultation", "Office Visit Progress Note", and "Orders Only Encounter" if it's tied to a clinical decision or lab review. "Telephone Encounter Note" is also a clinical encounter.
3.  **Filter out non-medical events:**
    *   "Telephone Encounter" (from Bridgewater Adolescent and Young Adult Medicine Briarwood) is a clinical interaction, so it's included.
    *   "Orders Only Encounter" (from Bridgewater Psychiatry Walnut Street) is a lab review, so it's included.
    *   "Orders Only Encounter" (from Bridgewater Heart and Vascular Center Briarwood) is for new lab orders, so it's included.
    *   "AETNA HEALTH - PRIOR AUTHORIZATION REQUEST" - Administrative, exclude.
    *   "Bridgewater Health - Scheduling Communication Log" - Administrative, exclude.
    *   "FAX COVER SHEET" - Administrative, exclude.
    *   "Bridgewater Health - Patient Billing Inquiry" - Administrative, exclude.
    *   "AETNA HEALTH - Member Services Correspondence" - Administrative, exclude.
    *   "Bridgewater Health - Provider Directory Update Notification" - **CRITICAL EXCLUSION: This is a provider list/directory update, exclude.**
    *   "Bridgewater Health - Patient Account Statement" - Administrative, exclude.
    *   "MyBridgewaterHealth Secure Message" - Patient message, not a clinical visit, exclude.
    *   "Chest X-Ray Report" - This is an imaging report, not a visit. The date of study is 08/19/2023, which is outside the scope of the provided notes (starting May 2, 2024 for clinical notes). Even if it were in scope, it's a report, not a visit.
    *   "Consent Forms" - Administrative/legal, exclude.
4.  **For each valid encounter, extract the required fields:**
    *   Date of Service
    *   Type of Visit
    *   Facility Name
    *   Provider Name
    *   Subjective/HPI/CC/Hospital Course
    *   Objective/PE
    *   Social
    *   Labs (significant abnormal results)
    *   Surgery/Procedure
    *   Imaging
    *   Diagnoses
    *   Plan/Assessment
    *   MSS
    *   Medication(s)
    *   Referrals
    *   Source References
5.  **Handle missing fields:** If a field is not explicitly present, write `Not specified`. Do not invent.
6.  **Handle "Orders Only Encounter"**: These are valid if they represent a clinical action (lab review, ordering labs).
7.  **Sort chronologically.**
8.  **Format strictly** according to the output rules.

Let's start extracting and filtering.

---
**Extraction and Filtering Pass:**

*   **Source:** EXHIBIT A: Bridgewater Psychiatry Walnut Street - Progress Notes & Correspondence
    *   **Encounter 1:** "Provider Note"
        *   Date of Service: May 2, 2024
        *   Facility Name: Bridgewater Psychiatry Walnut Street (implied by exhibit title)
        *   Provider Name: Liu, Andrew K, MD
        *   Type of Visit: Telemedicine / Behavioral Health Outpatient Clinic Follow-up
        *   Subjective: Return visit for medication management. Stable symptoms since Nov 2023. Unemployed, taking electrician classes. Sleep "ok". Weight increase 3-4 lbs. Denies clozapine side effects. Endorses chronic delusions (thought broadcasting, thought insertion). Denies SI/HI.
        *   Objective: MSE: Grooming appropriate, fair appearance effort, fair eye contact. No psychomotor agitation/retardation, no choreoathetoid movements. Speech normal rate/rhythm. Mood "Ok". Affect blunted, intermittently reactive. Thought process linear/goal-directed. Chronic delusions (thought broadcasting, thought insertion). Denies SI/HI. Denies auditory/visual hallucinations, not responding to internal stimuli. Alert/oriented. Insight fair to limited, judgment fair. Weight 218 lbs (Dr. Fischer estimate). Last recorded weight 12/19/23 was 231 lbs, BMI 34.11 kg/m². No EPS.
        *   Social: Unemployed, vocational training (electrical work). Resides with parents. Interested in SSI. Primary social outlet: online gaming.
        *   Labs: Orders placed for Hemoglobin A1c and Lipid Panel. Continue monthly CBC checks for ANC.
        *   Diagnoses: Schizophrenia, Paranoid type (F20.0); Hyperlipidemia; Long term current use of antipsychotic medication (Z79.899).
        *   Plan/Assessment: Continue clozapine 250 mg daily. Discussed Caplyta. Psychoeducation on lifestyle for weight management (exercise, diet, ketogenic diet). Encouraged follow-up with metabolic specialist. Follow-up in 5-6 months. Counseled on clozapine side effects.
        *   Medication(s): Clozapine 100 mg tablet (take 2.5 daily), Omega-3 fatty acids 1000 mg capsule (take 2 daily).
        *   Referrals: Continue follow-up with PCP for hypertriglyceridemia. Follow up with metabolic specialist.
        *   Source References: (Page 1 of 12)

    *   **Encounter 2:** "Provider Note"
        *   Date of Service: 2024-11-14
        *   Facility Name: Bridgewater Psychiatry Walnut Street (implied by exhibit title)
        *   Provider Name: Nair, Kavitha, MD
        *   Type of Visit: Telemedicine / Psychiatry Follow Up
        *   Subjective: Return visit for medication management. Period of stability, no significant changes. Lives with parents, electrician classes, unemployed. Sleep/mood unchanged. Occasional, fleeting paranoid thoughts (being watched/monitored). Morning grogginess (attributes to clozapine). Denies other side effects. Denies SI/HI.
        *   Objective: MSE: Hygiene/grooming appropriate. No abnormal motor activity. Cooperative, polite. Speech normal rate/rhythm. Mood "Fine". Affect mildly blunted but reactive. Thought process linear, organized, goal-directed. Denies SI/HI. Mild paranoia, no other overt delusions/grandiosity. Denies auditory/visual hallucinations. Grossly oriented. Insight/judgment fair. Euthymic with slightly blunted affect. No AVH/delusions, no RIS, no SI/HI.
        *   Social: No problematic alcohol, cannabis, nicotine use.
        *   Labs: Order for Clozapine level with next labs. Continue monthly ANC monitoring.
        *   Diagnoses: Paranoid schizophrenia (CMS-HCC) F20.0; Long term current use of antipsychotic medication Z79.89.
        *   Plan/Assessment: Continue clozapine 250 mg daily. Monitor response/tolerability. Return for follow-up in ~6 months. Psychoeducation. Encouraged continued follow-up with PCP. Risks/benefits of clozapine discussed. Not acute risk. Check cloz level, continue ANCs.
        *   Medication(s): Clozapine 250 mg tablet (take 2.5 daily at bedtime for 180 days).
        *   Source References: (Page 1 of 12)

    *   **Encounter 3:** "Telephone Encounter Note"
        *   Date of Call: 27-Dec-24
        *   Facility Name: Not specified (but associated with Nair, Kavitha, MD, likely Bridgewater Psychiatry Walnut Street)
        *   Provider Name: Nair, Kavitha, MD
        *   Type of Visit: Telephone Encounter (Medication Adjustment)
        *   Subjective: Patient's mother called regarding clozapine level slightly above 600.
        *   Plan/Assessment: Clozapine dose reduced from 250 mg to 225 mg. Recheck clozapine level in one month with next ANC. Mother verbalized understanding.
        *   Medication(s): Clozapine dose adjusted from 250 mg to 225 mg.
        *   Source References: (Page 1 of 12)

    *   **Encounter 4:** "Orders Only Encounter"
        *   Date of Service: 2025-01-27
        *   Facility Name: Not specified (but associated with Liu, Andrew K, MD, likely Bridgewater Psychiatry Walnut Street)
        *   Provider Name: Liu, Andrew K, MD
        *   Type of Visit: Lab Review
        *   Subjective: Not specified
        *   Objective: Recent lab results for HEME PROFILE + ELECT DIFF reviewed and acknowledged.
        *   Diagnoses: Paranoid schizaphrenia (CMS-HCC) [F20.0], Long term current use of antipsychotic medication [Z79.899].
        *   Plan/Assessment: No additional clinical findings or changes to plan of care documented.
        *   Source References: (Page 2 of 12)

*   **Source:** EXHIBIT B: Bridgewater Heart and Vascular Center Briarwood - Consultation Notes
    *   **Encounter 5:** "Bridgewater University Health System - Specialist Consultation"
        *   Date of Visit: December 17, 2024
        *   Facility Name: Bridgewater Heart and Vascular Center Briarwood
        *   Provider Name: Brennan, Thomas E, MD
        *   Type of Visit: Specialist Consultation (Follow-up for hyperlipidemia)
        *   Subjective: Follow-up appointment for hyperlipidemia. Patient attended with mother.
        *   Diagnoses: Combined hyperlipidemia; Class 1 obesity with serious comorbidity (BMI 34.0-34.9).
        *   Plan/Assessment: Recommendations for management of hyperlipidemia and obesity (dietary modification, regular physical activity, potential future pharmacologic interventions). Patient and mother verbalized understanding. Follow up as needed.
        *   Source References: (Page 2 of 12)

    *   **Encounter 6:** "Orders Only Encounter"
        *   Date of Service: Jan 7, 2025
        *   Facility Name: Not specified (but associated with Brennan, Thomas E, MD, likely Bridgewater Heart and Vascular Center Briarwood)
        *   Provider Name: Brennan, Thomas E, MD
        *   Type of Visit: Lab Orders
        *   Diagnoses: Combined hyperlipidemia (E78.2); Insulin resistance (R73.03).
        *   Plan/Assessment: New laboratory orders entered (LIPID PANEL W/ REFLEX TO DIRECT LDL, INSULIN, FASTING, COMPREHENSIVE METABOLIC PANEL). Patient to complete prior to next follow-up.
        *   Source References: (Page 3 of 12)

*   **Source:** EXHIBIT C: Bridgewater Adolescent and Young Adult Medicine Briarwood - Clinical Notes
    *   **Encounter 7:** "Telephone Encounter"
        *   Date: 12/26/2024
        *   Facility Name: Bridgewater Adolescent and Young Adult Medicine Briarwood
        *   Provider Name: Reyes, Gabriela, MD (Provider on Call), Documented by Cardenas, Rosa M, LPN
        *   Type of Visit: Telephone Encounter (Patient concern)
        *   Subjective: Patient expressed concern regarding hair loss.
        *   Plan/Assessment: Message routed to Dr. Reyes for review to determine if appointment needed. Patient advised they would call back.
        *   Source References: (Page 3 of 12)

    *   **Encounter 8:** "Office Visit Progress Note"
        *   Date of Service: February 10, 2025
        *   Facility Name: Bridgewater Adolescent and Young Adult Medicine Briarwood
        *   Provider Name: Reyes, Gabriela, MD
        *   Type of Visit: Office Visit
        *   Subjective: Primary concern: hair loss (occurring for some time). Attempted OTC remedies (rosemary oil, topical minoxidil) with no benefit. Family history of receding hair lines (mother's side) and male pattern baldness (father's side). Hypertriglyceridemia (followed by Dr. Brennan, off Lovaza, focusing on diet/exercise). Paranoid schizophrenia (followed by Bridgewater psychiatry, clozapine, monthly CBC monitoring, recent challenges with clozaril prescription).
        *   Objective: Vitals: BP 111/76, P 84, T 97.6F, Wt 227 lbs (103 kg), BMI 32.39 kg/m², SpO2 97%. PE: Moist mucous membranes, normal conjunctivae, normal heart rate/rhythm/sounds, normal respiratory effort/breath sounds. Skin warm/dry, no rash. Scalp exam: receding hair line anteriorly, no bald patches. Neuro: No focal deficits. Psych: Mood/behavior normal.
        *   Social: Applying for SSI, working with attorney Eleanor Caldwell.
        *   Diagnoses: Hair loss (L65.9) (likely androgenic alopecia); Hypertriglyceridemia (E78.1); Paranoid schizophrenia (F20.0).
        *   Plan/Assessment: Trial of oral minoxidil 1.25 mg daily. Follow-up in 2 months. Reinforced importance of lifestyle for hypertriglyceridemia. Clozapine management continues with Bridgewater psychiatry. Return in ~2 years for general follow-up/med check, or sooner.
        *   Medication(s): Oral minoxidil 1.25 mg daily.
        *   Source References: (Page 4 of 12)

*   **Source:** EXHIBIT D: Consolidated Laboratory Reports
    *   **Encounter 9:** "National Clinical Laboratories" - This is a lab report, not a visit. The ordering MD is Liu, Andrew K, MD, and the collection date is 05/02/2024, which aligns with the visit on 05/02/2024. I will include the lab results under the 05/02/2024 visit.
        *   Labs: Total Cholesterol 220 H, Triglycerides 397 H, HDL 27 L, VLDL 71 H, LDL 122 H. Hemoglobin A1C 5.2 (Normal).
        *   Source References: (Page 5 of 12)

    *   **Encounter 10:** "Allied Diagnostics - Patient Report" - This is a lab report, not a visit. The ordering MD is Nair, Kavitha, MD, and the collection date is 11/14/2024, which aligns with the visit on 11/14/2024. I will include the lab results under the 11/14/2024 visit.
        *   Labs: CBC/Differential - All within normal limits. ANC within normal limits for clozapine monitoring.
        *   Source References: (Page 5 of 12)

    *   **Encounter 11:** "Allied Diagnostics - Patient Report" - This is a lab report, not a visit. The ordering MD is Liu, Andrew K, MD, and the collection date is 01/27/2025, which aligns with the "Orders Only Encounter" on 01/27/2025. I will include the lab results under the 01/27/2025 lab review.
        *   Labs: CBC/Differential - All within normal limits. ANC within normal limits for clozapine monitoring.
        *   Source References: (Page 6 of 12)

*   **Source:** EXHIBIT F: Imaging Reports
    *   "Chest X-Ray Report" - Date of Study: 08/19/2023. This is outside the scope of the clinical notes provided (which start May 2024). Even if it were in scope, it's a report, not a visit. Exclude.

**Consolidate and Order:**

1.  **05/02/2024** - Bridgewater Psychiatry Walnut Street, Liu, Andrew K, MD (Provider Note)
    *   Labs: Total Cholesterol 220 H, Triglycerides 397 H, HDL 27 L, VLDL 71 H, LDL 122 H. Hemoglobin A1C 5.2 (Normal). (From National Clinical Labs report)

2.  **11/14/2024** - Bridgewater Psychiatry Walnut Street, Nair, Kavitha, MD (Provider Note)
    *   Labs: CBC/Differential - All within normal limits. ANC within normal limits. (From Allied Diagnostics report)

3.  **12/17/2024** - Bridgewater Heart and Vascular Center Briarwood, Brennan, Thomas E, MD (Specialist Consultation)

4.  **12/26/2024** - Bridgewater Adolescent and Young Adult Medicine Briarwood, Reyes, Gabriela, MD (Telephone Encounter)

5.  **12/27/2024** - Not specified (Nair, Kavitha, MD) (Telephone Encounter Note)

6.  **01/07/2025** - Not specified (Brennan, Thomas E, MD) (Orders Only Encounter - Lab Orders)

7.  **01/27/2025** - Not specified (Liu, Andrew K, MD) (Orders Only Encounter - Lab Review)
    *   Labs: CBC/Differential - All within normal limits. ANC within normal limits. (From Allied Diagnostics report)

8.  **02/10/2025** - Bridgewater Adolescent and Young Adult Medicine Briarwood, Reyes, Gabriela, MD (Office Visit Progress Note)

Now, I will format this according to the strict output rules. I need to ensure all fields are present, even if "Not specified". I will also ensure the source references are correctly placed.
I will explicitly state "Not specified" for Facility Name if it's not directly mentioned in the encounter header, even if it's implied by the exhibit title. The rule states "explicitly present in the text". For example, for the telephone encounter with Dr. Nair, the facility is not explicitly stated in that specific note, so it will be "Not specified". However, for the initial provider notes, the exhibit title "Bridgewater Psychiatry Walnut Street" is the context for the notes within that exhibit, so I will use that. For the "Orders Only Encounter" by Dr. Liu, it's under the Bridgewater Psychiatry Walnut Street exhibit, so I will use that. Same for Dr. Brennan's orders under Bridgewater Heart and Vascular Center Briarwood exhibit.

Re-evaluating Facility Names:
*   "Provider Note" (05/02/2024, Liu): Exhibit A is "Bridgewater Psychiatry Walnut Street". The note itself doesn't state the facility, but the exhibit title provides the context. I will use "Bridgewater Psychiatry Walnut Street".
*   "Provider Note" (11/14/2024, Nair): Same as above, "Bridgewater Psychiatry Walnut Street".
*   "Telephone Encounter Note" (12/27/2024, Nair): This note is within Exhibit A, "Bridgewater Psychiatry Walnut Street". So I will use "Bridgewater Psychiatry Walnut Street".
*   "Orders Only Encounter" (01/27/2025, Liu): This note is within Exhibit A, "Bridgewater Psychiatry Walnut Street". So I will use "Bridgewater Psychiatry Walnut Street".
*   "Specialist Consultation" (12/17/2024, Brennan): Exhibit B is "Bridgewater Heart and Vascular Center Briarwood". The note itself doesn't state the facility, but the exhibit title provides the context. I will use "Bridgewater Heart and Vascular Center Briarwood".
*   "Orders Only Encounter" (01/07/2025, Brennan): This note is within Exhibit B, "Bridgewater Heart and Vascular Center Briarwood". So I will use "Bridgewater Heart and Vascular Center Briarwood".
*   "Telephone Encounter" (12/26/2024, Reyes): Exhibit C is "Bridgewater Adolescent and Young Adult Medicine Briarwood". The note itself doesn't state the facility, but the exhibit title provides the context. I will use "Bridgewater Adolescent and Young Adult Medicine Briarwood".
*   "Office Visit Progress Note" (02/10/2025, Reyes): Same as above, "Bridgewater Adolescent and Young Adult Medicine Briarwood".

This interpretation aligns with "explicitly present in the text" if the exhibit title is considered part of the contextual text for the notes within it. If not, then many would be "Not specified". The prompt says "explicitly present in the text", and the exhibit title is text. I will use the exhibit title as the facility name for notes within that exhibit.

One more check on the lab results:
For 05/02/2024, the lab results are from a separate report (Exhibit D). The prompt says "Labs: (List significant abnormal results)". I should list them under the visit where they were ordered or reviewed. The 05/02/2024 note explicitly states "Orders were placed for a Hemoglobin A1c and a Lipid Panel". So, the lab results from 05/02/2024 collection date should be associated with this visit.
For 11/14/2024, the note says "An order will be placed to obtain a Clozapine level with his next set of labs." and "Continue monthly ANC monitoring." The Allied Diagnostics report for 11/14/2024 is a HEME PROFILE + ELECT DIFF (CBC/Differential), which is the ANC monitoring. So, these results should be associated with the 11/14/2024 visit.
For 01/27/2025, the "Orders Only Encounter" is a "Lab Review" for "HEME PROFILE + ELECT DIFF". The Allied Diagnostics report for 01/27/2025 is exactly this. So, these results should be associated with the 01/27/2025 lab review.

Final check on source references: I need to include the exact text, e.g., `(10E Page 27 of 43)`. The document uses `(Page X of 12)`. I will use that.

Let's construct the output.## Date of Medical Visit: 05/02/2024
### 05/02/2024
*   **Type of Visit:** Telemedicine / Behavioral Health Outpatient Clinic Follow-up
*   **Facility Name:** Bridgewater Psychiatry Walnut Street
*   **Provider Name:** Liu, Andrew K, MD
*   **Subjective/HPI/CC/Hospital Course:** Return visit for medication management. Patient, with mother, reports psychiatric symptoms stable since November 2023. Unemployed, actively searching for job while taking electrician classes. Sleep "ok" (midnight-12/1 PM). Denies recent appetite changes but notes 3-4 lb weight increase. Exercise intermittent. Denies clozapine side effects. Continues to endorse chronic delusions (thought broadcasting, thought insertion). Denies suicidal or homicidal ideation.
*   **Objective/PE:** Mental Status Examination: Grooming appropriate, fair appearance effort, fair eye contact. No psychomotor agitation/retardation, no choreoathetoid movements. Speech normal rate/rhythm. Mood "Ok". Affect predominantly blunted, intermittently reactive. Thought process linear and goal-directed. Content includes chronic delusions (thought broadcasting, thought insertion). Denies suicidal or homicidal ideation. Perception: Denies auditory/visual hallucinations, not responding to internal stimuli. Cognition: Alert and oriented. Insight fair to limited, judgment fair. Weight estimated at 218 lbs. Last recorded weight 12/19/23 was 231 lbs, BMI 34.11 kg/m². No EPS.
*   **Social:** Currently out of work, pursuing vocational training in electrical work. Resides with parents. Expressed interest in SSI benefits. Primary social outlet is online gaming.
*   **Labs:**
    *   Total Cholesterol: 220 mg/dL (H)
    *   Triglycerides: 397 mg/dL (H)
    *   HDL Cholesterol: 27 mg/dL (L)
    *   VLDL Cholesterol Cal: 71 mg/dL (H)
    *   LDL Cholesterol Calc: 122 mg/dL (H)
    *   Hemoglobin A1C: 5.2 % (Normal)
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Schizophrenia, Paranoid type (F20.0); Hyperlipidemia; Long term current use of antipsychotic medication (Z79.899).
*   **Plan/Assessment:** Continue clozapine 250 mg daily. Discussed potential benefits of considering Caplyta. Psychoeducation regarding lifestyle modifications for weight management (increase exercise, healthier diet, ketogenic diet mentioned). Encouraged follow-up with metabolic specialist. Follow-up in 5-6 months. Counseled on clozapine side effects. Orders placed for Hemoglobin A1c and Lipid Panel. Continue monthly CBC checks for ANC monitoring.
*   **MSS:** Not specified
*   **Medication(s):** Clozapine 100 mg tablet (take 2.5 tablets by mouth daily); Omega-3 fatty acids 1000 mg capsule (take 2 capsules by mouth daily).
*   **Referrals:** Continue follow-up with PCP for hypertriglyceridemia; Follow up with metabolic specialist.
*   **Source References:** (Page 1 of 12), (Page 5 of 12)

## Date of Medical Visit: 11/14/2024
### 11/14/2024
*   **Type of Visit:** Telemedicine / Psychiatry Follow Up
*   **Facility Name:** Bridgewater Psychiatry Walnut Street
*   **Provider Name:** Nair, Kavitha, MD
*   **Subjective/HPI/CC/Hospital Course:** Return visit for medication management. Patient indicates stability, no significant changes to mental health or life circumstances. Continues to live at home with parents, enrolled in electrician certification classes, not currently employed. Sleep and mood unchanged. Reports occasional, fleeting paranoid thoughts (being watched/monitored) a couple of times per month. Notes morning grogginess attributed to clozapine, denies other side effects. Denies suicidal or homicidal ideation.
*   **Objective/PE:** Mental Status Exam: Hygiene and grooming appropriate. No abnormal motor activity. Cooperative and polite. Speech normal rate and rhythm. Mood "Fine." Affect mildly blunted but reactive. Thought process linear, organized, and goal-directed. Denies SI/HI. Mild paranoia noted, no other overt delusions or grandiosity. Denies auditory or visual hallucinations. Grossly oriented. Insight and judgment fair. Euthymic with slightly blunted affect. No AVH/delusions, no RIS, no SI/HI.
*   **Social:** No problematic use of alcohol, cannabis, or nicotine reported.
*   **Labs:** CBC/Differential - All components within normal limits. ANC (Absolute Neutrophil Count) within normal limits for clozapine monitoring.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Paranoid schizophrenia (CMS-HCC) F20.0; Long term current use of antipsychotic medication Z79.89.
*   **Plan/Assessment:** Continue clozapine 250 mg by mouth daily. Monitor response and tolerability. Order for Clozapine level with next labs. Continue monthly ANC monitoring. Return for follow-up in approximately 6 months. Provided psychoeducation. Encouraged continued follow-up with PCP for general health maintenance. Risks and benefits of clozapine discussed. Current treatment plan appropriate for outpatient care, no acute risk.
*   **MSS:** Not specified
*   **Medication(s):** Clozapine 250 mg tablet (take 2.5 tablets by mouth daily at bedtime for 180 days).
*   **Referrals:** Not specified
*   **Source References:** (Page 1 of 12), (Page 5 of 12)

## Date of Medical Visit: 12/17/2024
### 12/17/2024
*   **Type of Visit:** Specialist Consultation
*   **Facility Name:** Bridgewater Heart and Vascular Center Briarwood
*   **Provider Name:** Brennan, Thomas E, MD
*   **Subjective/HPI/CC/Hospital Course:** Follow-up appointment stemming from original referral for detailed evaluation of hyperlipidemia. Patient attended with his mother.
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** Not specified
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Combined hyperlipidemia; Class 1 obesity with serious comorbidity (BMI of 34.0 to 34.9 in an adult, unspecified obesity type).
*   **Plan/Assessment:** Recommendations provided for management of combined hyperlipidemia and obesity. Detailed discussion regarding dietary modification, importance of regular physical activity, and potential future pharmacologic interventions if lifestyle changes are not sufficient. Patient and mother verbalized understanding. Follow up as needed.
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 2 of 12)

## Date of Medical Visit: 12/26/2024
### 12/26/2024
*   **Type of Visit:** Telephone Encounter
*   **Facility Name:** Bridgewater Adolescent and Young Adult Medicine Briarwood
*   **Provider Name:** Reyes, Gabriela, MD
*   **Subjective/HPI/CC/Hospital Course:** Patient expressed a concern regarding hair loss via telephone message.
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** Not specified
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Not specified
*   **Plan/Assessment:** Message routed to Dr. Reyes's clinical inbox for review and to determine if an appointment is needed. Patient was advised they would call him back.
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 3 of 12)

## Date of Medical Visit: 12/27/2024
### 12/27/2024
*   **Type of Visit:** Telephone Encounter (Medication Adjustment)
*   **Facility Name:** Bridgewater Psychiatry Walnut Street
*   **Provider Name:** Nair, Kavitha, MD
*   **Subjective/HPI/CC/Hospital Course:** Telephone call received from patient's mother regarding recent laboratory results. She stated that the clozapine level came back with a value slightly above 600.
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** Clozapine level slightly above 600.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Not specified
*   **Plan/Assessment:** Decision made to adjust patient's medication. Recheck clozapine level in one month, to be drawn at same time as next scheduled ANC. Mother verbalized understanding.
*   **MSS:** Not specified
*   **Medication(s):** Clozapine dose reduced from 250 mg to 225 mg.
*   **Referrals:** Not specified
*   **Source References:** (Page 1 of 12)

## Date of Medical Visit: 01/07/2025
### 01/07/2025
*   **Type of Visit:** Lab Orders
*   **Facility Name:** Bridgewater Heart and Vascular Center Briarwood
*   **Provider Name:** Brennan, Thomas E, MD
*   **Subjective/HPI/CC/Hospital Course:** Not specified
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** New laboratory orders entered: LIPID PANEL W/ REFLEX TO DIRECT LDL, INSULIN, FASTING, COMPREHENSIVE METABOLIC PANEL.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Combined hyperlipidemia (E78.2); Insulin resistance (R73.03).
*   **Plan/Assessment:** Patient to complete labs prior to next follow-up.
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 3 of 12)

## Date of Medical Visit: 01/27/2025
### 01/27/2025
*   **Type of Visit:** Lab Review
*   **Facility Name:** Bridgewater Psychiatry Walnut Street
*   **Provider Name:** Liu, Andrew K, MD
*   **Subjective/HPI/CC/Hospital Course:** Not specified
*   **Objective/PE:** Recent lab results for HEME PROFILE + ELECT DIFF were reviewed and acknowledged by the provider.
*   **Social:** Not specified
*   **Labs:** CBC/Differential - All components within normal limits. ANC (Absolute Neutrophil Count) within normal limits for clozapine monitoring.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Paranoid schizaphrenia (CMS-HCC) [F20.0]; Long term current use of antipsychotic medication [Z79.899].
*   **Plan/Assessment:** No additional clinical findings or changes to the plan of care were documented for this date.
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 2 of 12), (Page 6 of 12)

## Date of Medical Visit: 02/10/2025
### 02/10/2025
*   **Type of Visit:** Office Visit
*   **Facility Name:** Bridgewater Adolescent and Young Adult Medicine Briarwood
*   **Provider Name:** Reyes, Gabriela, MD
*   **Subjective/HPI/CC/Hospital Course:** Chief Complaint: Hair loss. Patient, with mother, presents with primary concern of hair loss occurring for some time. Attempted OTC remedies (rosemary oil, topical minoxidil) with no benefit. Family history of receding hair lines (mother's side) and male pattern baldness (father's side). Hypertriglyceridemia: Followed by Dr. Brennan, currently off Lovaza, focusing on diet and exercise. Paranoid schizophrenia: Followed by Bridgewater psychiatry, primary medication clozapine (requires monthly CBC monitoring), mentioned recent challenges with clozaril prescription.
*   **Objective/PE:** Vitals: BP 111/76 mmHg, P 84 bpm, T 97.6 F, Wt 227 lbs (103 kg), BMI 32.39 kg/m², SpO2 97% on room air. Physical Exam: Mouth/Throat: Mucous membranes moist. Eyes: Conjunctivae normal. Cardiovascular: Heart rate and rhythm normal, heart sounds normal. Pulmonary: Respiratory effort normal, normal breath sounds bilaterally. Skin: Warm and dry, no rash. Scalp: Receding hair line anteriorly, no bald patches. Neurological: No focal deficits. Psychiatric: Mood and behavior normal.
*   **Social:** In process of applying for SSI, working with attorney Eleanor Caldwell.
*   **Labs:** Not specified
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Hair loss (L65.9) (likely androgenic alopecia); Hypertriglyceridemia (E78.1); Paranoid schizophrenia (F20.0).
*   **Plan/Assessment:** Begin trial of oral minoxidil 1.25 mg daily. Follow-up in 2 months. Reinforced importance of lifestyle factors for hypertriglyceridemia. Clozapine management and monitoring to continue under Bridgewater psychiatry. Return in approximately 2 years for general follow-up and medication check, or sooner as needed.
*   **MSS:** Not specified
*   **Medication(s):** Oral minoxidil 1.25 mg daily.
*   **Referrals:** Not specified
*   **Source References:** (Page 4 of 12)