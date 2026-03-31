<scratchpad>
The user wants a chronological list of medical visits. I need to go through the document and extract relevant information for each valid medical encounter.

Here's my plan:
1.  **Iterate through the document section by section.**
2.  **For each potential entry, check if it's a valid medical visit.**
    *   Must have at least a Facility Name OR a Provider Name.
    *   Must be a clinical/medical visit (exclude legal, administrative, pharmacy fills, provider lists, etc.).
    *   Must have a Date of Service.
3.  **Extract all required fields for valid visits.**
    *   Type of Visit
    *   Facility Name
    *   Provider Name
    *   Subjective/HPI/CC/Hospital Course
    *   Objective/PE
    *   Social
    *   Labs
    *   Surgery/Procedure
    *   Imaging
    *   Diagnoses
    *   Plan/Assessment
    *   MSS
    *   Medication(s)
    *   Referrals
    *   Source References
4.  **Handle missing fields:** If a field is not explicitly present, write `Not specified`.
5.  **Handle dates:** Use "Date of Service". If only month/year, use MM/YYYY.
6.  **Sort chronologically.**
7.  **Format the output strictly as requested.**

Let's go through the document:

**EXHIBIT A: Bridgewater Psychiatry Walnut Street - Progress Notes & Correspondence**

*   **Provider Note - May 2, 2024**
    *   Date: 05/02/2024
    *   Type: Telemedicine / Behavioral Health Outpatient Clinic Follow-up
    *   Facility: Bridgewater Psychiatry Walnut Street
    *   Provider: Liu, Andrew K, MD
    *   Subjective: Return visit for medication management. Stable psychiatric symptoms since Nov 2023. Unemployed, taking electrician classes. Sleep "ok". Weight increase 3-4 lbs. Denies clozapine side effects. Endorses chronic delusions (thought broadcasting, thought insertion). Denies SI/HI.
    *   Objective: Appropriate grooming, fair appearance effort, fair eye contact. No psychomotor agitation/retardation, no choreoathetoid movements. Normal speech rate/rhythm. Mood "Ok". Affect blunted, intermittently reactive. Thought process linear, goal-directed. Chronic delusions (thought broadcasting, thought insertion). Denies SI/HI. Denies auditory/visual hallucinations, not responding to internal stimuli. Alert and oriented. Insight fair to limited, judgment fair. Weight 218 lbs (Dr. Fischer estimate). Last recorded weight 12/19/23 was 231 lbs, BMI 34.11 kg/m². No EPS.
    *   Social: Unemployed, vocational training in electrical work. Resides with parents. Interested in SSI. Primary social outlet: online gaming.
    *   Labs: Orders placed for Hemoglobin A1c and Lipid Panel. Continue monthly CBC checks for ANC.
    *   Diagnoses: Schizophrenia, Paranoid type (F20.0); Hyperlipidemia (managed by PCP); Long term current use of antipsychotic medication (Z79.899).
    *   Plan: Continue clozapine 250 mg daily. Discussed Caplyta. Psychoeducation on lifestyle for weight management (exercise, diet, ketogenic diet mentioned). Encourage follow-up with metabolic specialist. Follow-up in 5-6 months. Counseled on clozapine side effects.
    *   Medications: Clozapine 100 mg tablet (2.5 daily), Omega-3 fatty acids 1000 mg capsule (2 daily).
    *   Referrals: Continue follow-up with PCP for hypertriglyceridemia. Follow up with metabolic specialist.
    *   Source: (Page 1 of 12)

*   **National Clinical Laboratories - 05/02/2024** (Collection Date)
    *   Date: 05/02/2024
    *   Type: Lab Results
    *   Facility: National Clinical Laboratories
    *   Provider: Liu, Andrew K, MD (Ordering MD)
    *   Labs:
        *   LIPID SCREEN: Total Cholesterol 220 H (>200), Triglycerides 397 H (>150), HDL Cholesterol 27 L (>40), VLDL Cholesterol Cal 71 H (5-40), LDL Cholesterol Calc 122 H (<100). (Comment: LDL calculation invalid if triglycerides > 400 mg/dL).
        *   HEMOGLOBIN A1C: 5.2% (Normal).
    *   Source: (Page 4 of 12)

*   **Patient Billing Inquiry - 06/15/2024** - Administrative, exclude.
*   **Provider Directory Update Notification - 07/01/2024** - Administrative, exclude.

*   **Provider Note - 2024-11-14**
    *   Date: 11/14/2024
    *   Type: Telemedicine / Psychiatry Follow Up
    *   Facility: Bridgewater Psychiatry Walnut Street (implied by provider's primary practice location in directory update)
    *   Provider: Nair, Kavitha, MD
    *   Subjective: Return visit for medication management. Period of stability, no significant changes to mental health/life. Lives with parents, electrician classes, unemployed. Sleep/mood unchanged. Occasional, fleeting paranoid thoughts (feeling watched/monitored) a couple times/month. Morning grogginess attributed to clozapine, no other side effects. Denies SI/HI.
    *   Objective: Appropriate hygiene/grooming. No abnormal motor activity. Cooperative, polite. Normal speech rate/rhythm. Mood "Fine". Affect mildly blunted but reactive. Thought process linear, organized, goal-directed. Denies SI/HI. Mild paranoia, no other overt delusions/grandiosity. Denies auditory/visual hallucinations. Grossly oriented. Insight/judgment fair. Euthymic, slightly blunted affect. No AVH/delusions, no RIS, no SI/HI.
    *   Social: No problematic alcohol, cannabis, nicotine use.
    *   Diagnoses: Paranoid schizophrenia (CMS-HCC) F20.0 (Stable); Long term current use of antipsychotic medication Z79.89.
    *   Plan: Continue clozapine 250 mg daily. Monitor response/tolerability. Order clozapine level with next labs. Continue monthly ANC monitoring. Follow-up in ~6 months. Psychoeducation. Encourage PCP follow-up for general health. Risks/benefits of clozapine discussed. Not acute risk.
    *   Medications: Clozapine 250 mg tablet (2.5 daily at bedtime for 180 days).
    *   Source: (Page 1 of 12)

*   **Allied Diagnostics - 11/14/2024** (Collection Date)
    *   Date: 11/14/2024
    *   Type: Lab Results
    *   Facility: Allied Diagnostics
    *   Provider: Nair, Kavitha, MD (Ordering MD)
    *   Labs: HEME PROFILE + ELECT DIFF (CBC/Differential). All values within reference range. ANC (Absolute Neutrophil Count) within normal limits for clozapine monitoring.
    *   Source: (Page 4 of 12)

*   **AETNA HEALTH - PRIOR AUTHORIZATION REQUEST - 11/20/2024** - Administrative, exclude.
*   **Bridgewater Health - Scheduling Communication Log - 12/10/2024** - Administrative, exclude.

**EXHIBIT B: Bridgewater Heart and Vascular Center Briarwood - Consultation Notes**

*   **Bridgewater University Health System - Specialist Consultation - December 17, 2024**
    *   Date: 12/17/2024
    *   Type: Specialist Consultation (Follow-up for hyperlipidemia)
    *   Facility: Bridgewater Heart and Vascular Center Briarwood
    *   Provider: Brennan, Thomas E, MD
    *   Subjective: Follow-up appointment for hyperlipidemia. Patient attended with mother.
    *   Diagnoses: Combined hyperlipidemia; Class 1 obesity with serious comorbidity, BMI 34.0-34.9.
    *   Plan: Recommendations for management of hyperlipidemia and obesity. Discussion on dietary modification, regular physical activity, potential future pharmacologic interventions. Patient and mother verbalized understanding. Follow up as needed.
    *   Source: (Page 2 of 12)

*   **MyBridgewaterHealth Secure Message - 12/26/2024** - Patient message, not a visit. Exclude.

**EXHIBIT C: Bridgewater Adolescent and Young Adult Medicine Briarwood - Clinical Notes**

*   **Telephone Encounter - 12/26/2024**
    *   Date: 12/26/2024
    *   Type: Telephone Encounter
    *   Facility: Bridgewater Adolescent and Young Adult Medicine Briarwood (implied by provider)
    *   Provider: Reyes, Gabriela, MD (Provider on Call), Documented by Cardenas, Rosa M, LPN
    *   Subjective: Patient expressed concern regarding hair loss. Message routed to Dr. Reyes. Patient advised they would call back.
    *   Source: (Page 3 of 12)

*   **Telephone Encounter Note - 27-Dec-24**
    *   Date: 12/27/2024
    *   Type: Telephone Encounter
    *   Facility: Bridgewater Psychiatry Walnut Street (implied by provider Nair, Kavitha, MD)
    *   Provider: Nair, Kavitha, MD
    *   Subjective: Call from patient's mother regarding recent lab results (clozapine level slightly above 600).
    *   Plan: Clozapine dose reduced from 250 mg to 225 mg. Recheck clozapine level in one month with next scheduled ANC. Mother verbalized understanding.
    *   Source: (Page 1 of 12)

*   **Orders Only Encounter - Jan 7, 2025**
    *   Date: 01/07/2025
    *   Type: Orders Only Encounter
    *   Facility: Bridgewater Heart and Vascular Center Briarwood (implied by provider)
    *   Provider: Brennan, Thomas E, MD
    *   Diagnoses: Combined hyperlipidemia (E78.2); Insulin resistance (R73.03).
    *   Plan: New lab orders entered: LIPID PANEL W/ REFLEX TO DIRECT LDL, INSULIN, FASTING, COMPREHENSIVE METABOLIC PANEL. Patient to complete prior to next follow-up.
    *   Source: (Page 3 of 12)

*   **FAX COVER SHEET - January 16, 2025** - Administrative, exclude.

*   **Orders Only Encounter - 2025-01-27**
    *   Date: 01/27/2025
    *   Type: Orders Only Encounter / Lab Review
    *   Facility: Bridgewater Psychiatry Walnut Street (implied by provider)
    *   Provider: Liu, Andrew K, MD
    *   Subjective: Recent lab results for HEME PROFILE + ELECT DIFF reviewed and acknowledged. No additional clinical findings or changes to plan of care documented.
    *   Diagnoses: Paranoid schizophrenia (CMS-HCC) [F20.0], Long term current use of antipsychotic medication [Z79.899].
    *   Source: (Page 2 of 12)

*   **Allied Diagnostics - 01/27/2025** (Collection Date)
    *   Date: 01/27/2025
    *   Type: Lab Results
    *   Facility: Allied Diagnostics
    *   Provider: Liu, Andrew K, MD (Ordering MD)
    *   Labs: HEME PROFILE + ELECT DIFF (CBC/Differential). All values within reference range. ANC (Absolute Neutrophil Count) within normal limits for clozapine monitoring.
    *   Source: (Page 5 of 12)

*   **Office Visit Progress Note - February 10, 2025**
    *   Date: 02/10/2025
    *   Type: Office Visit Progress Note
    *   Facility: Bridgewater Adolescent and Young Adult Medicine Briarwood
    *   Provider: Reyes, Gabriela, MD
    *   Subjective: Patient with mother, primary concern hair loss. Occurring for some time. Attempted OTC remedies (rosemary oil, topical minoxidil) with no benefit. Family history of receding hair lines (mother's side) and male pattern baldness (father's side). Hypertriglyceridemia followed by Dr. Brennan, off Lovaza, focusing on diet/exercise. Paranoid schizophrenia followed by Bridgewater psychiatry, primary med clozapine, monthly CBC monitoring. Recent challenges filling clozaril prescription.
    *   Objective: Vitals: BP 111/76, Pulse 84, Temp 97.6, Weight 227 lbs (103 kg), BMI 32.39 kg/m², SpO2 97%. Physical Exam: Moist mucous membranes, normal conjunctivae, normal heart rate/rhythm/sounds, normal respiratory effort/breath sounds. Skin warm/dry, no rash. Scalp exam: receding hair line anteriorly, no bald patches. No focal neurological deficits. Mood/behavior normal.
    *   Social: Applying for SSI, working with attorney Eleanor Caldwell.
    *   Diagnoses: Hair loss (L65.9) (likely androgenic alopecia); Hypertriglyceridemia (E78.1); Paranoid schizophrenia (F20.0).
    *   Plan: Trial of oral minoxidil 1.25 mg daily. Follow-up in 2 months. Reinforced importance of lifestyle for hypertriglyceridemia. Clozapine management by Bridgewater psychiatry. Return in ~2 years for general follow-up/med check, or sooner.
    *   Medications: Oral minoxidil 1.25 mg daily.
    *   Source: (Page 3 of 12)

*   **Bridgewater Health - Patient Account Statement - 02/28/2025** - Administrative, exclude.

**Consents and other administrative documents:**
*   AETNA HEALTH - Member Services Correspondence - 04/30/2024 - Administrative, exclude.
*   Chest X-Ray Report - 08/19/2023 - This is an imaging report, not a visit. However, it has an ordering physician. I need to decide if "Imaging" is a "Type of Visit" or if it should be listed under a visit where it was ordered. The prompt asks for "Type of Visit" (Primary Care, Orthopedic, Pulmonary, Hospital Admission, Exam, PT, etc). An X-ray report itself isn't a "visit" in the same way. The prompt also has "Imaging" as a field. I will list it as an Imaging result under the visit where it was ordered if possible, but if it's a standalone report without an associated visit, I will list it as a "Radiology Study" type of visit. In this case, the ordering physician is Fischer, Nathan, MD, but there's no corresponding visit note for 08/19/2023. So, I will treat it as a standalone entry.
    *   Date: 08/19/2023
    *   Type: Radiology Study (Chest X-Ray)
    *   Facility: Bridgewater Health - Department of Radiology
    *   Provider: Mehta, Sunita, MD (Radiologist), Fischer, Nathan, MD (Ordering Physician)
    *   Subjective: 24-year-old male with cough. Rule out pneumonia.
    *   Imaging: Cardiomediastinal silhouette WNL. Pulmonary vasculature unremarkable. Lungs clear. No focal consolidation, pleural effusion, or pneumothorax. Osseous structures intact. Soft tissues unremarkable.
    *   Diagnoses: No acute cardiopulmonary process.
    *   Source: (Page 10 of 12)

*   Consent Forms (01/05/2023, 04/15/2023, 01/05/2023) - Administrative, exclude.

Now, sort chronologically.

1.  08/19/2023 - Radiology Study (Chest X-Ray)
2.  05/02/2024 - Telemedicine / Behavioral Health Outpatient Clinic Follow-up (Liu)
3.  05/02/2024 - Lab Results (Liu)
4.  11/14/2024 - Telemedicine / Psychiatry Follow Up (Nair)
5.  11/14/2024 - Lab Results (Nair)
6.  12/17/2024 - Specialist Consultation (Brennan)
7.  12/26/2024 - Telephone Encounter (Reyes)
8.  12/27/2024 - Telephone Encounter (Nair)
9.  01/07/2025 - Orders Only Encounter (Brennan)
10. 01/27/2025 - Orders Only Encounter / Lab Review (Liu)
11. 01/27/2025 - Lab Results (Liu)
12. 02/10/2025 - Office Visit Progress Note (Reyes)

Looks good. I will now format it according to the strict output rules.
I need to ensure that for each date, the `## Date of Medical Visit: MM/DD/YYYY` is followed by `### MM/DD/YYYY` for each distinct visit on that day.
For the lab results, I will list the ordering provider as the "Provider Name" and the lab facility as "Facility Name".
For the Chest X-Ray, I will list both the radiologist and ordering physician.

Re-checking the "Provider Name" for labs: The prompt says "Provider Name: (If applicable.)". For lab results, the ordering MD is applicable. For the X-ray, both the radiologist and ordering physician are applicable. I will list both for the X-ray. For labs, I will list the ordering MD.

Let's refine the X-ray entry:
*   **Type of Visit:** Radiology Study (Chest X-Ray)
*   **Facility Name:** Bridgewater Health - Department of Radiology
*   **Provider Name:** Mehta, Sunita, MD (Radiologist); Fischer, Nathan, MD (Ordering Physician)
*   **Subjective/HPI/CC/Hospital Course:** 24-year-old male with cough. Rule out pneumonia.
*   **Imaging:** Cardiomediastinal silhouette within normal limits for size and contour. Pulmonary vasculature unremarkable. Lungs clear. No evidence of focal consolidation, pleural effusion, or pneumothorax. Visualized osseous structures of the thorax are intact and without acute abnormality. Soft tissues of the chest wall are unremarkable.
*   **Diagnoses:** No acute cardiopulmonary process.
*   **Source References:** (Page 10 of 12)

This looks correct. I will proceed with generating the output.## Date of Medical Visit: 08/19/2023
### 08/19/2023
*   **Type of Visit:** Radiology Study (Chest X-Ray)
*   **Facility Name:** Bridgewater Health - Department of Radiology
*   **Provider Name:** Mehta, Sunita, MD (Radiologist); Fischer, Nathan, MD (Ordering Physician)
*   **Subjective/HPI/CC/Hospital Course:** 24-year-old male with cough. Rule out pneumonia.
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** Not specified
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Cardiomediastinal silhouette is within normal limits for size and contour. The pulmonary vasculature is unremarkable. The lungs are clear. There is no evidence of focal consolidation, pleural effusion, or pneumothorax. Visualized osseous structures of the thorax are intact and without acute abnormality. The soft tissues of the chest wall are unremarkable.
*   **Diagnoses:** No acute cardiopulmonary process.
*   **Plan/Assessment:** Not specified
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 10 of 12)

## Date of Medical Visit: 05/02/2024
### 05/02/2024
*   **Type of Visit:** Telemedicine / Behavioral Health Outpatient Clinic Follow-up
*   **Facility Name:** Bridgewater Psychiatry Walnut Street
*   **Provider Name:** Liu, Andrew K, MD
*   **Subjective/HPI/CC/Hospital Course:** Return visit for medication management. Psychiatric symptoms stable since November 2023. Unemployed, actively searching for a job while taking electrician classes. Sleep "ok" (midnight-12/1 PM). Denies recent changes in appetite but notes 3-4 lb weight increase. Exercise intermittent. Denies clozapine side effects. Continues to endorse chronic delusions (thought broadcasting, thought insertion). Denies suicidal or homicidal ideation.
*   **Objective/PE:** Mental Status Examination: Grooming appropriate, fair effort to appearance. Eye contact fair. No psychomotor agitation or retardation, no choreoathetoid movements. Speech normal rate/rhythm. Mood "Ok". Affect predominantly blunted, intermittently reactive. Thought process linear, goal-directed. Content includes chronic delusions (thought broadcasting, thought insertion). Denies suicidal or homicidal ideation. Perception: Denies auditory or visual hallucinations, not responding to internal stimuli. Cognition: Alert and oriented. Insight fair to limited, judgment fair. Weight estimated at 218 lbs (Dr. Fischer). Last recorded weight 12/19/23 was 231 lbs, BMI 34.11 kg/m². Pleasant man, weight gain noted. Speech mostly expressive. No EPS noted.
*   **Social:** Unemployed, pursuing vocational training in electrical work. Resides with parents. Expressed interest in applying for SSI benefits. Primary social outlet is online gaming.
*   **Labs:** Orders placed for Hemoglobin A1c and Lipid Panel. Will need to continue monthly CBC checks for ANC monitoring as per clozapine protocol.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Schizophrenia, Paranoid type (F20.0); Hyperlipidemia; Long term current use of antipsychotic medication (Z79.899).
*   **Plan/Assessment:** Continue current regimen of clozapine at 250 mg daily. Discussed potential benefits of considering Caplyta in the future. Provided psychoeducation regarding lifestyle modifications for weight management (increase exercise, healthier diet, ketogenic diet mentioned). Encouraged follow up with metabolic specialist again. Follow-up in 5-6 months. Counseled on clozapine side effects.
*   **MSS:** Not specified
*   **Medication(s):** Clozapine 100 mg tablet (2.5 tablets by mouth daily); Omega-3 fatty acids 1000 mg capsule (2 capsules by mouth daily).
*   **Referrals:** Continue follow-up with PCP for hypertriglyceridemia. Follow up with metabolic specialist as previously recommended.
*   **Source References:** (Page 1 of 12)

### 05/02/2024
*   **Type of Visit:** Lab Results
*   **Facility Name:** National Clinical Laboratories
*   **Provider Name:** Liu, Andrew K, MD
*   **Subjective/HPI/CC/Hospital Course:** Not specified
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:**
    *   LIPID SCREEN: Total Cholesterol 220 mg/dL (H), Triglycerides 397 mg/dL (H), HDL Cholesterol 27 mg/dL (L), VLDL Cholesterol Cal 71 mg/dL (H), LDL Cholesterol Calc 122 mg/dL (H).
    *   HEMOGLOBIN A1C: 5.2% (Normal).
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Not specified
*   **Plan/Assessment:** Not specified
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 4 of 12)

## Date of Medical Visit: 11/14/2024
### 11/14/2024
*   **Type of Visit:** Telemedicine / Psychiatry Follow Up
*   **Facility Name:** Not specified
*   **Provider Name:** Nair, Kavitha, MD
*   **Subjective/HPI/CC/Hospital Course:** Return visit for medication management. Reports period of stability, no significant changes to mental health or overall life circumstances. Continues to live at home with parents, enrolled in electrician certification classes. Not currently employed. Sleep and mood unchanged. Reports occasional, fleeting paranoid thoughts (feeling watched or monitored) a couple of times per month. Notes morning grogginess attributed to clozapine, denies other side effects. Denies suicidal or homicidal ideation.
*   **Objective/PE:** Mental Status Exam: Attention to hygiene and grooming appropriate. No abnormal motor activity. Cooperative and polite. Speech normal rate and rhythm. Mood "Fine". Affect mildly blunted but reactive. Thought process linear, organized, and goal-directed. Denies SI/HI. Mild paranoia noted, no other overt delusions or grandiosity. Denies auditory or visual hallucinations. Grossly oriented. Insight and judgment fair. Euthymic with slightly blunted affect. No AVH/delusions, no RIS, no SI/HI.
*   **Social:** No problematic use of alcohol, cannabis, or nicotine reported.
*   **Labs:** Order will be placed to obtain a Clozapine level with next set of labs. Continue monthly ANC monitoring.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Paranoid schizophrenia (CMS-HCC) F20.0 (Stable on current treatment); Long term current use of antipsychotic medication Z79.89.
*   **Plan/Assessment:** Continue clozapine 250 mg by mouth daily. Monitor response and tolerability. Patient to return for follow-up in approximately 6 months. Provided psychoeducation. Encouraged continued follow-up with PCP for general health maintenance. Risks and benefits of clozapine discussed. Current treatment plan remains appropriate for outpatient care. Not deemed to be at any acute risk. Will check cloz level and continue to follow ANCs.
*   **MSS:** Not specified
*   **Medication(s):** Clozapine 250 mg tablet (2.5 tablets by mouth daily at bedtime for 180 days).
*   **Referrals:** Not specified
*   **Source References:** (Page 1 of 12)

### 11/14/2024
*   **Type of Visit:** Lab Results
*   **Facility Name:** Allied Diagnostics
*   **Provider Name:** Nair, Kavitha, MD
*   **Subjective/HPI/CC/Hospital Course:** Not specified
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** HEME PROFILE + ELECT DIFF (CBC/Differential): All components (WBC, RBC, Hemoglobin, Hematocrit, MCV, MCH, MCHC, RDW, Platelets, Neutrophils %, Lymphs %, Monocytes %, Eos %, Basos %, Neutrophils (Absolute), Lymphs (Absolute), Monocytes (Absolute), Eos (Absolute), Baso (Absolute), Immature Granulocytes %, Immature Grans (Abs)) within reference ranges. ANC (Absolute Neutrophil Count) is within normal limits for clozapine monitoring.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Not specified
*   **Plan/Assessment:** Not specified
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 4 of 12)

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
*   **Diagnoses:** Combined hyperlipidemia; Class 1 obesity with serious comorbidity, body mass index (BMI) of 34.0 to 34.9 in an adult, unspecified obesity type.
*   **Plan/Assessment:** Recommendations provided for management of combined hyperlipidemia and obesity. Detailed discussion regarding dietary modification, importance of regular physical activity, and potential future pharmacologic interventions if lifestyle changes are not sufficient. Patient and mother verbalized understanding. Follow up as needed.
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 2 of 12)

## Date of Medical Visit: 12/26/2024
### 12/26/2024
*   **Type of Visit:** Telephone Encounter
*   **Facility Name:** Bridgewater Adolescent and Young Adult Medicine Briarwood
*   **Provider Name:** Reyes, Gabriela, MD; Cardenas, Rosa M, LPN
*   **Subjective/HPI/CC/Hospital Course:** Patient expressed concern regarding hair loss.
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** Not specified
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Not specified
*   **Plan/Assessment:** Message routed to Dr. Reyes for review to determine if an appointment is needed. Patient advised they would call him back.
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 3 of 12)

## Date of Medical Visit: 12/27/2024
### 12/27/2024
*   **Type of Visit:** Telephone Encounter
*   **Facility Name:** Not specified
*   **Provider Name:** Nair, Kavitha, MD
*   **Subjective/HPI/CC/Hospital Course:** Telephone call received from patient's mother regarding recent laboratory results. Clozapine level came back slightly above 600.
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** Clozapine level slightly above 600.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Not specified
*   **Plan/Assessment:** Decision made to adjust patient's medication. Daily dose of clozapine reduced from 250 mg to 225 mg. Plan to recheck clozapine level in one month, to be drawn at same time as next scheduled ANC. Mother verbalized understanding.
*   **MSS:** Not specified
*   **Medication(s):** Clozapine (dose adjusted from 250 mg to 225 mg).
*   **Referrals:** Not specified
*   **Source References:** (Page 1 of 12)

## Date of Medical Visit: 01/07/2025
### 01/07/2025
*   **Type of Visit:** Orders Only Encounter
*   **Facility Name:** Not specified
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
*   **Type of Visit:** Orders Only Encounter / Lab Review
*   **Facility Name:** Not specified
*   **Provider Name:** Liu, Andrew K, MD
*   **Subjective/HPI/CC/Hospital Course:** Recent lab results for HEME PROFILE + ELECT DIFF were reviewed and acknowledged by the provider. No additional clinical findings or changes to the plan of care were documented for this date.
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** HEME PROFILE + ELECT DIFF reviewed.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Paranoid schizophrenia (CMS-HCC) [F20.0]; Long term current use of antipsychotic medication [Z79.899].
*   **Plan/Assessment:** Not specified
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 2 of 12)

### 01/27/2025
*   **Type of Visit:** Lab Results
*   **Facility Name:** Allied Diagnostics
*   **Provider Name:** Liu, Andrew K, MD
*   **Subjective/HPI/CC/Hospital Course:** Not specified
*   **Objective/PE:** Not specified
*   **Social:** Not specified
*   **Labs:** HEME PROFILE + ELECT DIFF (CBC/Differential): All components (WBC, RBC, Hemoglobin, Hematocrit, MCV, MCH, MCHC, RDW, Platelets, Neutrophils %, Lymphs %, Monocytes %, Eos %, Basos %, Neutrophils (Absolute), Lymphs (Absolute), Monocytes (Absolute), Eos (Absolute), Baso (Absolute), Immature Granulocytes %, Immature Grans (Abs)) within reference ranges. ANC (Absolute Neutrophil Count) is within normal limits for clozapine monitoring.
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Not specified
*   **Plan/Assessment:** Not specified
*   **MSS:** Not specified
*   **Medication(s):** Not specified
*   **Referrals:** Not specified
*   **Source References:** (Page 5 of 12)

## Date of Medical Visit: 02/10/2025
### 02/10/2025
*   **Type of Visit:** Office Visit Progress Note
*   **Facility Name:** Bridgewater Adolescent and Young Adult Medicine Briarwood
*   **Provider Name:** Reyes, Gabriela, MD
*   **Subjective/HPI/CC/Hospital Course:** Patient presents with mother, primary concern of hair loss. Occurring for some time. Attempted OTC remedies (rosemary oil, topical minoxidil) with no benefit. Family history of receding hair lines (mother's side) and male pattern baldness (father's side). Hypertriglyceridemia followed by Dr. Brennan, currently off Lovaza, focusing on diet and exercise. Paranoid schizophrenia followed by Bridgewater psychiatry, primary medication clozapine, requires monthly CBC monitoring. Mentioned recent challenges with getting clozaril prescription filled.
*   **Objective/PE:** Vitals: BP 111/76 mmHg, Pulse 84 bpm, Temp 97.6 F, Weight 227 lbs (103 kg), BMI 32.39 kg/m², SpO2 97% on room air. Physical Exam: Mouth/Throat: Mucous membranes moist. Eyes: Conjunctivae appear normal. Cardiovascular: Heart rate and rhythm normal, heart sounds normal. Pulmonary: Respiratory effort normal, normal breath sounds bilaterally. Skin: Warm and dry, no rash. Scalp: Receding hair line anteriorly, no bald patches. Neurological: No focal deficits. Psychiatric: Mood and behavior appear normal.
*   **Social:** In process of applying for SSI, working with an attorney.
*   **Labs:** Not specified
*   **Surgery/Procedure:** Not specified
*   **Imaging:** Not specified
*   **Diagnoses:** Hair loss (L65.9) (likely androgenic alopecia); Hypertriglyceridemia (E78.1); Paranoid schizophrenia (F20.0).
*   **Plan/Assessment:** Begin trial of oral minoxidil at 1.25 mg daily. Follow-up in 2 months to evaluate response. Reinforced importance of lifestyle factors for hypertriglyceridemia. Clozapine management and monitoring to continue under Bridgewater psychiatry team. Return in approximately 2 years for general follow-up and medication check, or sooner as needed.
*   **MSS:** Not specified
*   **Medication(s):** Oral minoxidil 1.25 mg daily.
*   **Referrals:** Not specified
*   **Source References:** (Page 3 of 12)