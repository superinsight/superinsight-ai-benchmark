<think>Let me carefully analyze the source document to extract all medical visits according to the specified criteria.

First, I need to identify all potential encounters:

1. **May 2, 2024** - Bridgewater Psychiatry Walnut Street - Dr. Liu, Andrew K, MD - Telemedicine/Behavioral Health Outpatient Clinic Follow-up
   - This is a clinical visit with provider name and facility name

2. **November 14, 2024** - Bridgewater Psychiatry - Dr. Nair, Kavitha, MD - Telemedicine/Psychiatry Follow Up
   - This is a clinical visit with provider name and facility name

3. **December 27, 2024** - Telephone call from patient's mother to Dr. Nair, Kavitha, MD
   - This is a telephone encounter, but it involves clinical decision-making (medication adjustment)
   - Has provider name

4. **January 27, 2025** - "Orders Only Encounter" - Dr. Liu, Andrew K, MD
   - Lab review - "Purpose: Lab Review"
   - Has provider name
   - This is a clinical encounter involving reviewing lab results and making medication decisions

5. **December 17, 2024** - Bridgewater Heart and Vascular Center Briarwood - Dr. Brennan, Thomas E, MD
   - Specialist Consultation - has facility and provider

6. **January 7, 2025** - "Orders Only Encounter" - Dr. Brennan, Thomas E, MD
   - Lab orders only - has provider name
   - This is placing orders, but is it a clinical visit? It's an "Orders Only Encounter"

7. **December 26, 2024** - Telephone message to Dr. Reyes, Gabriela, MD
   - Patient called about hair loss
   - Has provider name
   - This is a telephone encounter, not a visit

8. **February 10, 2025** - Bridgewater Adolescent and Young Adult Medicine Briarwood - Dr. 
Reyes, Gabriela, MD
   - Office visit - has facility and provider

Now I need to apply the filtering rules:

**Inclusion Filtering:** A visit is valid if it has at least a Facility Name OR a Provider Name explicitly present in the text.

Let me check each:

1. May 2, 2024 - Has both: "Bridgewater Psychiatry Walnut Street" and "Liu, Andrew K, MD" - VALID
2. November 14, 2024 - Has "Bridgewater Psychiatry" and "Nair, Kavitha, MD" - VALID
3. December 27, 2024 - Has "Nair, Kavitha, MD" - VALID (telephone but clinical)
4. January 27, 2025 - Has "Liu, Andrew K, MD" - VALID (Orders Only Encounter)
5. December 17, 2024 - Has "Bridgewater Heart and Vascular Center Briarwood" and "Brennan, Thomas E, MD" - VALID
6. January 7, 2025 - Has "Brennan, Thomas E, MD" - VALID (Orders Only Encounter)
7. December 26, 2024 - Has "Reyes, Gabriela, MD" - This is a telephone message, not a visit
8. February 10, 2025 - Has "Bridgewater Adolescent and Young Adult Medicine Briarwood" and "Reyes, Gabriela, MD" - VALID

**Scope Filtering:**
- Discard all legal events (depositions, legal reviews) - None here
- Discard "Provider Lists", "Directories", "Staff Updates", "Medical Provider List Updates", or "Summaries of Treating Providers" - None here
- Discard non-medical events (billing, admin) - Need to check

Let me review what's in the document:
- EXHIBIT A: Bridgewater Psychiatry Walnut Street - Progress Notes & Correspondence - CLINICAL
- EXHIBIT B: Bridgewater Heart and Vascular Center Briarwood - Consultation Notes - CLINICAL
- EXHIBIT C: Bridgewater Adolescent and Young Adult Medicine Briarwood - Clinical Notes - CLINICAL
- EXHIBIT D: Consolidated Laboratory Reports - These are lab results, not visits themselves
- EXHIBIT E: Administrative and Billing Records - This is administrative/billing - EXCLUDE
- EXHIBIT F: Imaging Reports - Chest X-Ray from 08/19/2023 - This is an imaging study, not a visit
- EXHIBIT G: Consent Forms - Administrative - EXCLUDE

Now, regarding the "Orders Only Encounter" notes:
- January 27, 2025: "Purpose: Lab Review" - This is a clinical encounter where the provider reviewed lab results and acknowledged them. This is a medical visit.
- January 7, 2025: "New laboratory orders have been entered" - This is placing orders, but it's documented as an "Orders Only Encounter" with a specific date of service. This appears to be a clinical encounter.

The telephone encounters are trickier:
- December 27, 2024: Telephone call from mother regarding lab results, medication adjustment made - This is a clinical encounter
- December 26, 2024: Telephone message received from patient regarding hair loss - This is a message, not a visit

Let me reconsider the "Orders Only Encounter" entries. Looking at the format:
- "Orders Only Encounter" on 2025-01-27 with Provider: Liu, Andrew K, MD - "Purpose: Lab Review" - This is a clinical encounter
- "Orders Only Encounter" on Jan 7, 2025 with Ordering Provider: Brennan, Thomas E, MD - This is placing lab orders

The question is: Are these "visits"? Looking at the instructions:
- Include only clinical/medical visits where a patient was seen or treated.
- Exclude: Legal events, pharmacy fills, administrative calls, scheduling notes, billing/insurance notes.

The "Orders Only Encounter" on January 27, 2025 appears to be a clinical encounter where the provider reviewed lab results. This is a medical encounter.

The "Orders Only Encounter" on January 7, 2025 appears to be placing orders. This might be considered administrative, but it's documented as an encounter with a date of service.

Let me also check the imaging report:
- Chest X-Ray from 08/19/2023 - This is an imaging study, not a visit. The ordering physician is Dr. Fischer, Nathan, MD, but this is just an imaging result, not a visit.

Now let me sort chronologically:

1. May 2, 2024 - Bridgewater Psychiatry Walnut Street - Dr. Liu, Andrew K, MD
2. November 14, 2024 - Bridgewater Psychiatry - Dr. Nair, Kavitha, MD
3. December 17, 2024 - Bridgewater Heart and Vascular Center Briarwood - Dr. Brennan, Thomas E, MD
4. December 26, 2024 - Telephone message (not a visit)
5. December 27, 2024 - Telephone call (clinical encounter)
6. January 7, 2025 - Orders Only Encounter - Dr. Brennan, Thomas E, MD
7. January 27, 2025 - Orders Only Encounter - Dr. Liu, Andrew K, MD
8. February 10, 2025 - Bridgewater Adolescent and Young Adult Medicine Briarwood - Dr. Reyes, Gabriela, MD

Wait, I need to check if December 26 and December 27 should be included. The instructions say:
- Include only clinical/medical visits where a patient was seen or treated.
- Exclude: administrative calls, scheduling notes

December 27, 2024: "A telephone call was received from the patient's mother regarding recent laboratory results... Based on this information, a decision was made to adjust the patient's medication."

This is a clinical encounter where a medical decision was made (medication adjustment). This should be included.

December 26, 2024: "A telephone message was received from the patient. He expressed a concern regarding hair loss. A message was routed to Dr. Reyes's clinical inbox for review and to determine if an appointment is needed."

This is just a message, not a clinical encounter where the patient was seen or treated. This should be EXCLUDED.

Now for the "Orders Only Encounter" entries:
- January 7, 2025: This is placing lab orders. Is this a clinical visit? It's documented as an encounter with a date of service and provider name. But it's just placing orders.
- January 27, 2025: This is lab review. "Recent lab results for HEME PROFILE + ELECT DIFF were reviewed and acknowledged by the provider."

The January 27, 2025 entry seems more like a clinical encounter because it involves reviewing results and making decisions. The January 7, 2025 entry is just placing orders.

However, looking at the instructions again:
- "Include only clinical/medical visits where a patient was seen or treated."

The "Orders Only Encounter" entries don't involve the patient being seen. They are provider-only documentation. But they do have dates of service and provider names.

Let me be conservative and include both since they have provider names and dates of service, and they are part of the medical record. But I need to be careful about whether they are truly "visits."

Actually, looking at the format, these "Orders Only Encounter" entries appear to be clinical encounters where the provider is documenting their review of results or ordering of labs. They are part of the patient's medical care.

Let me finalize the list:

1. May 2, 2024 - Bridgewater Psychiatry Walnut Street - Dr. Liu, Andrew K, MD - Telemedicine
2. November 14, 2024 - Bridgewater Psychiatry - Dr. Nair, Kavitha, MD - Telemedicine
3. December 17, 2024 - Bridgewater Heart and Vascular Center Briarwood - Dr. Brennan, Thomas E, MD - Consultation
4. December 27, 2024 - Telephone encounter - Dr. Nair, Kavitha, MD - Lab results call
5. January 7, 2025 - Orders Only Encounter - Dr. Brennan, Thomas E, MD - Lab orders
6. January 27, 2025 - Orders Only Encounter - Dr. Liu, Andrew K, MD - Lab review
7. February 10, 2025 - Bridgewater Adolescent and Young Adult Medicine Briarwood - Dr. Reyes, Gabriela, MD - Office visit

Wait, I need to check if there are any other visits I missed. Let me re-read the document carefully.

Looking at EXHIBIT D (Lab Reports):
- Lab tests were run on 05/02/2024, 11/14/2024, and 01/27/2025
- These are lab results, not visits themselves

Looking at EXHIBIT F (Imaging Reports):
- Chest X-Ray from 08/19/2023 - This is outside the date range (the document is from 2024-2025), and it's just an imaging report, not a visit

Now, let me check if there are any other entries I might have missed. Let me look at the billing section (EXHIBIT E):
- This is administrative/billing - EXCLUDE

Now, I need to format the output according to the instructions:

## Field Definitions (Exact Order)
1. **Type of Visit:** (Primary Care, Orthopedic, Pulmonary, Hospital Admission, Exam, PT, etc)
2. **Facility Name:** (If applicable. Do **NOT** use street addresses as Facility Names.)
3. **Provider Name:** (If applicable.)
4. **Subjective/HPI/CC/Hospital Course:** (Patient complaints, history)
5. **Objective/PE:** (Vitals, physical exam findings)
6. **Social:** (Flag Alcohol, Tobacco, or Substance/DAA use)
7. **Labs:** (List significant abnormal results)
8. **Surgery/Procedure:** (Specific procedures performed)
9. **Imaging:** (MRI, X-ray, CT findings)
10. **Diagnoses:** (Medical codes or named diagnoses)
11. **Plan/Assessment:** (Treatment plan, discharge instructions)
12. **MSS:** (Musculoskeletal specific findings)
13. **Medication(s):** (Drugs prescribed)
14. **Referrals:** (To PT, surgeons, etc.)
15. **Source References:** (Include the exact source reference text found in the document, e.g., `(10E Page 27 of 43)` or `<!-- Source... -->`)

Now let me extract the information for each visit:

**1. May 2, 2024**
- Type of Visit: Telemedicine / Behavioral Health Outpatient Clinic Follow-up
- Facility Name: Bridgewater Psychiatry Walnut Street
- Provider Name: Liu, Andrew K, MD
- Subjective/HPI/CC/Hospital Course: Return visit for medication management. Patient reports psychiatric symptoms stable since last appointment in November 2023. Currently unemployed but actively searching for job while taking classes to become an electrician. Sleep "ok" from around midnight until 12:00 or 1:00 PM. Denies recent changes in appetite but notes weight increase of 3-4 pounds. Exercise intermittent. Denies side effects from clozapine. Continues to endorse chronic delusions (thought broadcasting and thought insertion). Denies suicidal or homicidal ideation.
- Objective/PE: Mental Status Examination: Grooming appropriate. Eye contact fair. No psychomotor agitation/retardation, no choreoathetoid movements. Speech normal rate and rhythm. Mood "Ok". Affect blunted but intermittently reactive. Thought process linear and goal-directed. Content includes chronic delusions (thought broadcasting and thought insertion). Denies SI/HI. No auditory or visual hallucinations. Alert and oriented. Insight fair to limited, judgment fair. Weight 218 lbs. No EPS noted.
- Social: Out of work, pursuing vocational training in electrical work, resides with parents, interested in applying for SSI, primary social outlet online gaming.
- Labs: Last recorded weight 12/19/23 was 231 lbs, BMI 34.11 kg/m². Weight now 218 lbs.
- Diagnoses: Schizophrenia, Paranoid type (F20.0), Hyperlipidemia, Long term current use of antipsychotic medication (Z79.899)
- Plan/Assessment: Continue clozapine 250 mg daily. Discussed potential benefits of Caplyta. Metabolic monitoring - orders for Hemoglobin A1c and Lipid Panel. Continue monthly CBC for ANC monitoring. Psychoeducation regarding lifestyle modifications for weight management. Follow up in 5-6 months.
- Medications: Clozapine 100 mg tablet, take 2.5 tablets by mouth daily. Omega-3 fatty acids 1000 mg capsule, take 2 capsules by mouth daily.
- Referrals: Continue follow-up with PCP for hypertriglyceridemia. Follow up with metabolic specialist.
- Source References: (10E Page 27 of 43) - Wait, I need to find the actual source reference. Looking at the document, it's from "EXHIBIT A: Bridgewater Psychiatry Walnut Street - Progress Notes & Correspondence" and it's on Page 1 of 12. So the source reference should be something like "(10A Page 1 of 12)" or similar. Actually, looking at the format, it seems like the source reference should be in the format `(Page X of Y)` but I need to determine the correct exhibit letter. Looking at the document structure, it's EXHIBIT A, so it would be `(10A Page 1 of 12)`.

Wait, let me check the format again. The instructions say: "Include the exact source reference text found in the document, e.g., `(10E Page 27 of 43)` or `<!-- Source... -->`"

Looking at the document, I don't see explicit source reference markers like "(10E Page 27 of 43)". The document has page numbers at the bottom of each page (e.g., "Page 1 of 12"). So I should use something like "(EXHIBIT A Page 1 of 12)" or just "(Page 1 of 12)".

Actually, looking more carefully at the document, I see that each page has "PATIENT: DOE, JOHN A. | MRN: 987654321 | CLAIM#: PA-2025-XYZ-001 | Page X of 12" at the top. So I should use that as the source reference.

Let me re-read the instructions: "Include the exact source reference text found in the document, e.g., `(10E Page 27 of 43)`"

This seems to be an example format. Looking at the document, I don't see "10E" anywhere. The document has exhibits labeled A through G. So maybe the format is different.

Let me just use the page numbers as they appear in the document. Each page has "Page X of 12" at the top. So for May 2, 2024, it's on Page 1 of 12.

Actually, looking at the document more carefully, I see that the source references in the example are like "(10E Page 27 of 43)". This might be a specific format used in legal documents. Since I don't see that format in this document, I'll just use the page numbers as they appear.

Let me continue with the extraction:

**2. November 14, 2024**
- Type of Visit: Telemedicine / Psychiatry Follow Up
- Facility Name: Bridgewater Psychiatry (Market Street)
- Provider Name: Nair, Kavitha, MD
- Subjective/HPI/CC/Hospital Course: Return visit for medication management. Patient indicates period of stability, no significant changes to mental health or life circumstances. Continues to live at home with parents, enrolled in classes for electrician certification. Not currently employed. Sleep and mood unchanged. Occasional fleeting paranoid thoughts a couple times per month (feelings of being watched or monitored). Morning grogginess attributed to clozapine, denies other side effects. Explicitly denies SI/HI.
- Objective/PE: Mental Status Exam: Attention to hygiene and grooming appropriate. No abnormal motor activity. Cooperative and polite. Speech normal rate and rhythm. Mood "Fine". Affect mildly blunted but reactive. Thought process linear, organized, goal-directed. Mild paranoia noted, no other overt delusions or grandiosity. Denies auditory or visual hallucinations. Grossly oriented. Insight and judgment fair. Euthymic with slightly blunted affect. No AVH/delusions, no RIS, no SI/HI.
- Social: No problematic use of alcohol, cannabis, or nicotine.
- Labs: None mentioned in this note
- Diagnoses: Paranoid schizophrenia (CMS-HCC) F20.0, Long term current use of antipsychotic medication Z79.89
- Plan/Assessment: Continue clozapine 250 mg daily. Monitor response and tolerability. Order will be placed to obtain Clozapine level with next set of labs. Continue monthly ANC monitoring. Return in approximately 6 months. Psychoeducation provided. Encourage follow-up with PCP for general health maintenance. Risks and benefits of clozapine discussed. Not at acute risk. Check cloz level and continue to follow ANCs.
- Medications: Clozapine 250 mg tablet, take 2.5 tablets by mouth daily at bedtime for 180 days.
- Referrals: None specifically mentioned
- Source References: (Page 2 of 12)

**3. December 17, 2024**
- Type of Visit: Specialist Consultation - Follow-up for hyperlipidemia
- Facility Name: Bridgewater Heart and Vascular Center Briarwood
- Provider Name: Brennan, Thomas E, MD
- Subjective/HPI/CC/Hospital Course: Follow-up appointment stemming from original referral for detailed evaluation of hyperlipidemia (HL). Patient attended with mother.
- Objective/PE: [Not detailed in the note - just assessment and plan]
- Social: [Not mentioned]
- Labs: [Not mentioned]
- Diagnoses: 1. Combined hyperlipidemia. 2. Class 1 obesity with serious comorbidity, BMI of 34.0 to 34.9 in an adult, unspecified obesity type.
- Plan/Assessment: Recommendations provided for management of combined hyperlipidemia and obesity. Detailed discussion regarding dietary modification, importance of regular physical activity, potential future pharmacologic interventions if lifestyle changes not sufficient. Patient and mother verbalized understanding. Follow up as needed.
- Medications: [Not mentioned]
- Referrals: [Not mentioned]
- Source References: (Page 3 of 12)

**4. December 27, 2024**
- Type of Visit: Telephone Encounter
- Facility Name: Not specified (Telephone call)
- Provider Name: Nair, Kavitha, MD
- Subjective/HPI/CC/Hospital Course: Telephone call received from patient's mother regarding recent laboratory results. Mother stated clozapine level came back with value slightly above 600.
- Objective/PE: [Not applicable for telephone call]
- Social: [Not mentioned]
- Labs: Clozapine level slightly above 600
- Diagnoses: [Not mentioned in this note]
- Plan/Assessment: Decision made to adjust medication. Daily dose of clozapine reduced from 250 mg to 225 mg. Plan to recheck clozapine level in one month, to be drawn at same time as next scheduled ANC. Mother verbalized understanding.
- Medications: Clozapine adjusted from 250 mg to 225 mg daily
- Referrals: [Not mentioned]
- Source References: (Page 2 of 12)

**5. January 7, 2025**
- Type of Visit: Orders Only Encounter
- Facility Name: Not specified
- Provider Name: Brennan, Thomas E, MD
- Subjective/HPI/CC/Hospital Course: [Not applicable]
- Objective/PE: [Not applicable]
- Social: [Not mentioned]
- Labs: [Not applicable - just ordering labs]
- Diagnoses: Primary Dx: Combined hyperlipidemia (E78.2), Secondary Dx: Insulin resistance (R73.03)
- Plan/Assessment: New laboratory orders entered: Lipid Panel w/ Reflex to Direct LDL, Insulin Fasting, Comprehensive Metabolic Panel. Order transmitted to preferred lab. Patient to complete prior to next follow-up.
- Medications: [Not mentioned]
- Referrals: [Not mentioned]
- Source References: (Page 3 of 12)

**6. January 27, 2025**
- Type of Visit: Orders Only Encounter - Lab Review
- Facility Name: Not specified
- Provider Name: Liu, Andrew K, MD
- Subjective/HPI/CC/Hospital Course: Purpose: Lab Review. Recent lab results for HEME PROFILE + ELECT DIFF were reviewed and acknowledged by the provider.
- Objective/PE: [Not applicable]
- Social: [Not mentioned]
- Labs: [Lab results reviewed - but need to check if there are findings. Looking at the lab results in EXHIBIT D, the CBC from 01/27/2025 shows WBC 4.4, RBC 5.47, etc. ANC is within normal limits.]
- Diagnoses: Paranoid schizophrenia (CMS-HCC) [F20.0], Long term current use of antipsychotic medication [Z79.899]
- Plan/Assessment: No additional clinical findings or changes to the plan of care documented for this date.
- Medications: [Not mentioned]
- Referrals: [Not mentioned]
- Source References: (Page 2 of 12)

**7. February 10, 2025**
- Type of Visit: Office Visit - Primary Care/Adolescent Medicine
- Facility Name: Bridgewater Adolescent and Young Adult Medicine Briarwood
- Provider Name: Reyes, Gabriela, MD
- Subjective/HPI/CC/Hospital Course: Chief complaint: Hair loss. Patient presents with primary concern of hair loss. Reports this has been occurring for some time. Attempted over-the-counter remedies including rosemary oil and topical minoxidil, no benefit. Family history of receding hair lines on mother's side and male pattern baldness on father's side.
- Objective/PE: Vitals: BP 111/76 mmHg, Pulse 84 bpm, Temp 97.6 F, Weight 227 lbs (103 kg), BMI 32.39 kg/m², SpO2 97% on room air. Physical Exam: Mouth/Throat - mucous membranes moist. Eyes - conjunctivae normal. Cardiovascular - heart rate and rhythm normal, heart sounds normal. Pulmonary - respiratory effort normal, breath sounds normal bilaterally. Skin - warm and dry, no rash. Scalp examination reveals receding hair line anteriorly, no bald patches. Neurological - no focal deficits. Psychiatric - mood and behavior normal.
- Social: Patient in process of applying for SSI, working with attorney Eleanor Caldwell.
- Labs: [Not mentioned]
- Diagnoses: 1. Hair loss (L65.9) - likely androgenic alopecia. 2. Hypertriglyceridemia (E78.1). 3. Paranoid schizophrenia (F20.0).
- Plan/Assessment: Begin trial of oral minoxidil at 1.25 mg daily. Follow-up appointment in 2 months to evaluate response. Reinforced importance of lifestyle factors for hypertriglyceridemia (diet and exercise). Management of clozapine and monitoring to continue under Bridgewater psychiatry. Return in approximately 2 years for general follow-up and medication check, or sooner as needed.
- Medications: Oral minoxidil 1.25 mg daily
- Referrals: [Not mentioned]
- Source References: (Page 4 of 12)

Now I need to check if there are any other visits I missed. Let me re-read the document one more time.

Looking at the document again:
- The Chest X-Ray from 08/19/2023 is outside the date range and is just an imaging report, not a visit.
- The billing and administrative sections (EXHIBIT E) should be excluded.
- The consent forms (EXHIBIT G) should be excluded.

Now, I need to check if there are any other clinical encounters I might have missed. Let me look at the telephone message on December 26, 2024 again:

"**Telephone Encounter**
Patient: Doe, John A.
MRN: 987654321
Date: 12/26/2024
Provider on Call: Reyes, Gabriela, MD
Documented by: Cardenas, Rosa M, LPN

A telephone message was received from the patient. He expressed a concern regarding hair loss. A message was routed to Dr. Reyes's clinical inbox for review and to determine if an appointment is needed. Patient was advised we would call him back."

This is just a telephone message, not a clinical visit where the patient was seen or treated. This should be EXCLUDED.

Now, let me also check if there are any other visits I might have missed. Looking at the document again, I see:

- The lab reports in EXHIBIT D are not visits themselves, they are results of visits.
- The imaging report in EXHIBIT F is from 2023, outside the date range.

So I believe I have all the visits:

1. May 2, 2024
2. November 14, 2024
3. December 17, 2024
4. December 27, 2024
5. January 7, 2025
6. January 27, 2025
7. February 10, 2025

Now I need to format the output according to the instructions. Let me check the date format again:

"**Heading Level 2:** Use the exact format `## Date of Medical Visit: MM/DD/YYYY` (create this once per calendar day)."

So I need to group by date:

- May 2, 2024
- November 14, 2024
- December 17, 2024
- December 27, 2024
- January 7, 2025
- January 27, 2025
- February 10, 2025

Each date gets an H2, then an H3 under it.

Wait, the instructions say: "**Heading Level 3:** Immediately under H2, use the format `### MM/DD/YYYY` (or `### MM/YYYY` if day is missing)."

So the format is:
## Date of Medical Visit: MM/DD/YYYY
### MM/DD/YYYY
* Content

Actually, looking at the example:
## Date of Medical Visit: 09/15/2022
### 09/15/2022
* **Type of Visit:** Orthopedics Clinic Note

So it seems like the H2 and H3 both have the same date. That's a bit redundant, but that's the format.

Now, let me check if there are any same-day visits that need separate entries. Looking at the dates:
- May 2, 2024 - only one visit
- November 14, 2024 - only one visit
- December 17, 2024 - only one visit
- December 27, 2024 - only one visit
- January 7, 2025 - only one visit
- January 27, 2025 - only one visit
- February 10, 2025 - only one visit

No same-day visits.

Now, let me check the field order again:
1. Type of Visit
2. Facility Name
3. Provider Name
4. Subjective/HPI/CC/Hospital Course
5. Objective/PE
6. Social
7. Labs
8. Surgery/Procedure
9. Imaging
10. Diagnoses
11. Plan/Assessment
12. MSS
13. Medication(s)
14. Referrals
15. Source References

I need to make sure I have all fields for each visit, even if they're empty.

Let me also check if I need to include any specific details from the lab reports. The lab reports are in EXHIBIT D, but they are attached to specific visits. For example, the lab results from May 2, 2024 are mentioned in the psychiatry note. The lab results from November 14, 2024 are mentioned in the psychiatry note. The lab results from January 27, 2025 are mentioned in the "Orders Only Encounter" note.

Actually, looking at the lab reports in EXHIBIT D, there are three sets of labs:
1. Lipid Screen and Hemoglobin A1C from 05/02/2024
2. HEME PROFILE + ELECT DIFF from 11/14/2024
3. HEME PROFILE + ELECT DIFF from 01/27/2025

These are lab results, not visits. But they are associated with visits. I should include the significant abnormal results in the Labs field for the corresponding visits.

For May 2, 2024:
- Total Cholesterol: 220 H (ref <200)
- Triglycerides: 397 H (ref <150)
- HDL Cholesterol: 27 L (ref >40)
- VLDL Cholesterol Cal: 71 H (ref 5-40)
- LDL Cholesterol Calc: 122 H (ref <100)
- Hemoglobin A1C: 5.2 (normal)

For November 14, 2024:
- CBC results are all within normal limits

For January 27, 2025:
- CBC results are all within normal limits

Now, let me also check if there are any imaging studies. The Chest X-Ray from 08/19/2023 is outside the date range and is just an imaging report, not a visit. So I won't include it.

Now, let me also check if there are any surgeries or procedures. None mentioned.

Now, let me also check if there are any MSS (musculoskeletal) findings. None mentioned.

Now, let me format the output. I'll start with the first visit and work through each one chronologically.

Wait, I need to check the source references again. Looking at the document, each page has "Page X of 12" at the top. But I also need to identify which exhibit each visit is from. Let me check:

- May 2, 2024: EXHIBIT A (Bridgewater Psychiatry Walnut Street) - Page 1 of 12
- November 14, 2024: EXHIBIT A - Page 2 of 12
- December 17, 2024: EXHIBIT B (Bridgewater Heart and Vascular Center Briarwood) - Page 3 of 12
- December 27, 2024: EXHIBIT A - Page 2 of 12
- January 7, 2025: EXHIBIT B - Page 3 of 12
- January 27, 2025: EXHIBIT A - Page 2 of 12
- February 10, 2025: EXHIBIT C (Bridgewater Adolescent and Young Adult Medicine Briarwood) - Page 4 of 12

So the source references would be something like:
- (EXHIBIT A, Page 1 of 12)
- (EXHIBIT A, Page 2 of 12)
- (EXHIBIT B, Page 3 of 12)
- (EXHIBIT C, Page 4 of 12)

But looking at the instructions again: "Include the exact source reference text found in the document, e.g., `(10E Page 27 of 43)`"

This format seems to be a specific legal format. Since I don't see that exact format in the document, I'll just use the page numbers as they appear.

Actually, looking at the document more carefully, I see that the page numbers are at the top of each page: "PATIENT: DOE, JOHN A. | MRN: 987654321 | CLAIM#: PA-2025-XYZ-001 | Page X of 12"

So I should use that format. But I also need to identify the exhibit. Let me just use "Page X of 12" since that's what appears on each page.

Wait, but the instructions say to include the "exact source reference text found in the document". So I should use exactly what's in the document. Looking at the document, each page has "Page X of 12" at the top. So I'll use that.

Actually, looking at the example again: "(10E Page 27 of 43)". This seems to be a page number within an exhibit (10E might mean exhibit 10, page E? Or maybe it's just a page number). 

I'll proceed with using the page numbers as they appear in the document.

Now, let me format the output:

## Date of Medical Visit: 05/02/2024
### 05/02/2024
* **Type of Visit:** Telemedicine / Behavioral Health Outpatient Clinic Follow-up
* **Facility Name:** Bridgewater Psychiatry Walnut Street
* **Provider Name:** Liu, Andrew K, MD
* **Subjective/HPI/CC/Hospital Course:** Return visit for medication management. Patient reports psychiatric symptoms stable since last appointment in November 2023. Currently unemployed but actively searching for job while taking classes to become an electrician. Sleep "ok" from around midnight until 12:00 or 1:00 PM. Denies recent changes in appetite but notes weight increase of 3-4 pounds. Exercise intermittent. Denies side effects from clozapine. Continues to endorse chronic delusions (thought broadcasting and thought insertion). Denies suicidal or homicidal ideation.
* **Objective/PE:** Mental Status Examination: Grooming appropriate. Eye contact fair. No psychomotor agitation/retardation, no choreoathetoid movements. Speech normal rate and rhythm. Mood "Ok". Affect blunted but intermittently reactive. Thought process linear and goal-directed. Content includes chronic delusions (thought broadcasting and thought insertion). Denies SI/HI. No auditory or visual hallucinations. Alert and oriented. Insight fair to limited, judgment fair. Weight 218 lbs. No EPS noted.
* **Social:** Out of work, pursuing vocational training in electrical work, resides with parents, interested in applying for SSI, primary social outlet online gaming.
* **Labs:** Weight 218 lbs (down from 231 lbs on 12/19/23). BMI 34.11 kg/m². Lipid Panel: Total Cholesterol 220 H, Triglycerides 397 H, HDL Cholesterol 27 L, VLDL Cholesterol 71 H, LDL Cholesterol 122 H. Hemoglobin A1C 5.2 (normal).
* **Diagnoses:** Schizophrenia, Paranoid type (F20.0); Hyperlipidemia; Long term current use of antipsychotic medication (Z79.899)
* **Plan/Assessment:** Continue clozapine 250 mg daily. Discussed potential benefits of Caplyta. Metabolic monitoring - orders for Hemoglobin A1c and Lipid Panel. Continue monthly CBC for ANC monitoring. Psychoeducation regarding lifestyle modifications for weight management. Follow up in 5-6 months.
* **Medication(s):** Clozapine 100 mg tablet, take 2.5 tablets by mouth daily; Omega-3 fatty acids 1000 mg capsule, take 2 capsules by mouth daily
* **Referrals:** Continue follow-up with PCP for hypertriglyceridemia; Follow up with metabolic specialist
* **Source References:** (Page 1 of 12)

## Date of Medical Visit: 11/14/2024
### 11/14/2024
* **Type of Visit:** Telemedicine / Psychiatry Follow Up
* **Facility Name:** Bridgewater Psychiatry Walnut Street
* **Provider Name:** Nair, Kavitha, MD
* **Subjective/HPI/CC/Hospital Course:** Return visit for medication management. Patient indicates period of stability, no significant changes to mental health or life circumstances. Continues to live at home with parents, enrolled in classes for electrician certification. Not currently employed. Sleep and mood unchanged. Occasional fleeting paranoid thoughts a couple times per month (feelings of being watched or monitored). Morning grogginess attributed to clozapine, denies other side effects. Explicitly denies SI/HI.
* **Objective/PE:** Mental Status Exam: Attention to hygiene and grooming appropriate. No abnormal motor activity. Cooperative and polite. Speech normal rate and rhythm. Mood "Fine". Affect mildly blunted but reactive. Thought process linear, organized, goal-directed. Mild paranoia noted, no other overt delusions or grandiosity. Denies auditory or visual hallucinations. Grossly oriented. Insight and judgment fair. Euthymic with slightly blunted affect. No AVH/delusions, no RIS, no SI/HI.
* **Social:** No problematic use of alcohol, cannabis, or nicotine.
* **Labs:** CBC within normal limits
* **Diagnoses:** Paranoid schizophrenia (CMS-HCC) F20.0; Long term current use of antipsychotic medication Z79.89
* **Plan/Assessment:** Continue clozapine 250 mg daily. Monitor response and tolerability. Order will be placed to obtain Clozapine level with next set of labs. Continue monthly ANC monitoring. Return in approximately 6 months. Psychoeducation provided. Encourage follow-up with PCP for general health maintenance. Risks and benefits of clozapine discussed. Not at acute risk. Check cloz level and continue to follow ANCs.
* **Medication(s):** Clozapine 250 mg tablet, take 2.5 tablets by mouth daily at bedtime for 180 days
* **Referrals:** None
* **Source References:** (Page 2 of 12)

## Date of Medical Visit: 12/17/2024
### 12/17/2024
* **Type of Visit:** Specialist Consultation - Follow-up for hyperlipidemia
* **Facility Name:** Bridgewater Heart and Vascular Center Briarwood
* **Provider Name:** Brennan, Thomas E, MD
* **Subjective/HPI/CC/Hospital Course:** Follow-up appointment stemming from original referral for detailed evaluation of hyperlipidemia (HL). Patient attended with mother.
* **Objective/PE:** [Not detailed in note]
* **Social:** [Not mentioned]
* **Labs:** [Not mentioned]
* **Diagnoses:** Combined hyperlipidemia; Class 1 obesity with serious comorbidity, BMI of 34.0 to 34.9 in an adult, unspecified obesity type
* **Plan/Assessment:** Recommendations provided for management of combined hyperlipidemia and obesity. Detailed discussion regarding dietary modification, importance of regular physical activity, potential future pharmacologic interventions if lifestyle changes not sufficient. Patient and mother verbalized understanding. Follow up as needed.
* **Medication(s):** [Not mentioned]
* **Referrals:** [Not mentioned]
* **Source References:** (Page 3 of 12)

## Date of Medical Visit: 12/27/2024
### 12/27/2024
* **Type of Visit:** Telephone Encounter
* **Facility Name:** Not specified
* **Provider Name:** Nair, Kavitha, MD
* **Subjective/HPI/CC/Hospital Course:** Telephone call received from patient's mother regarding recent laboratory results. Mother stated clozapine level came back with value slightly above 600.
* **Objective/PE:** [Not applicable]
* **Social:** [Not mentioned]
* **Labs:** Clozapine level slightly above 600
* **Diagnoses:** [Not mentioned]
* **Plan/Assessment:** Decision made to adjust medication. Daily dose of clozapine reduced from 250 mg to 225 mg. Plan to recheck clozapine level in one month, to be drawn at same time as next scheduled ANC. Mother verbalized understanding.
* **Medication(s):** Clozapine adjusted from 250 mg to 225 mg daily
* **Referrals:** [Not mentioned]
* **Source References:** (Page 2 of 12)

## Date of Medical Visit: 01/07/2025
### 01/07/2025
* **Type of Visit:** Orders Only Encounter
* **Facility Name:** Not specified
* **Provider Name:** Brennan, Thomas E, MD
* **Subjective/HPI/CC/Hospital Course:** [Not applicable]
* **Objective/PE:** [Not applicable]
* **Social:** [Not mentioned]
* **Labs:** [Not applicable - just ordering labs]
* **Diagnoses:** Primary Dx: Combined hyperlipidemia (E78.2); Secondary Dx: Insulin resistance (R73.03)
* **Plan/Assessment:** New laboratory orders entered: Lipid Panel w/ Reflex to Direct LDL, Insulin Fasting, Comprehensive Metabolic Panel. Order transmitted to preferred lab. Patient to complete prior to next follow-up.
* **Medication(s):** [Not mentioned]
* **Referrals:** [Not mentioned]
* **Source References:** (Page 3 of 12)

## Date of Medical Visit: 01/27/2025
### 01/27/2025
* **Type of Visit:** Orders Only Encounter - Lab Review
* **Facility Name:** Not specified
* **Provider Name:** Liu, Andrew K, MD
* **Subjective/HPI/CC/Hospital Course:** Purpose: Lab Review. Recent lab results for HEME PROFILE + ELECT DIFF were reviewed and acknowledged by the provider.
* **Objective/PE:** [Not applicable]
* **Social:** [Not mentioned]
* **Labs:** CBC within normal limits (WBC 4.4, RBC 5.47, Hemoglobin 15.5, Hematocrit 46.3, Platelets 194, ANC within normal limits)
* **Diagnoses:** Paranoid schizophrenia (CMS-HCC) [F20.0]; Long term current use of antipsychotic medication [Z79.899]
* **Plan/Assessment:** No additional clinical findings or changes to the plan of care documented for this date.
* **Medication(s):** [Not mentioned]
* **Referrals:** [Not mentioned]
* **Source References:** (Page 2 of 12)

## Date of Medical Visit: 02/10/2025
### 02/10/2025
* **Type of Visit:** Office Visit - Primary Care/Adolescent Medicine
* **Facility Name:** Bridgewater Adolescent and Young Adult Medicine Briarwood
* **Provider Name:** Reyes, Gabriela, MD
* **Subjective/HPI/CC/Hospital Course:** Chief complaint: Hair loss. Patient presents with primary concern of hair loss. Reports this has been occurring for some time. Attempted over-the-counter remedies including rosemary oil and topical minoxidil, no benefit. Family history of receding hair lines on mother's side and male pattern baldness on father's side.
* **Objective/PE:** Vitals: BP 111/76 mmHg, Pulse 84 bpm, Temp 97.6 F, Weight 227 lbs (103 kg), BMI 32.39 kg/m², SpO2 97% on room air. Physical Exam: Mouth/Throat - mucous membranes moist. Eyes - conjunctivae normal. Cardiovascular - heart rate and rhythm normal, heart sounds normal. Pulmonary - respiratory effort normal, breath sounds normal bilaterally. Skin - warm and dry, no rash. Scalp examination reveals receding hair line anteriorly, no bald patches. Neurological - no focal deficits. Psychiatric - mood and behavior normal.
* **Social:** Patient in process of applying for SSI, working with attorney Eleanor Caldwell.
* **Labs:** [Not mentioned]
* **Diagnoses:** Hair loss (L65.9) - likely androgenic alopecia; Hypertriglyceridemia (E78.1); Paranoid schizophrenia (F20.0)
* **Plan/Assessment:** Begin trial of oral minoxidil at 1.25 mg daily. Follow-up appointment in 2 months to evaluate response. Reinforced importance of lifestyle factors for hypertriglyceridemia (diet and exercise). Management of clozapine and monitoring to continue under Bridgewater psychiatry. Return in approximately 2 years for general follow-up and medication check, or sooner as needed.
* **Medication(s):** Oral minoxidil 1.25 mg daily
* **Referrals:** [Not mentioned]
* **Source References:** (Page 4 of 12)

Now I need to double-check if I should include the telephone message on December 26, 2024. Looking at the instructions:

"Include only clinical/medical visits where a patient was seen or treated.
- Exclude: Legal events, pharmacy fills, administrative calls, scheduling notes, billing/insurance notes."

The telephone message on December 26, 2024 is just a message from the patient expressing a concern. It's not a clinical visit where the patient was seen or treated. It's more like a scheduling or administrative call. So I should exclude it.

Also, I need to check if I should include the "Orders Only Encounter" entries. Looking at the instructions:

"Include only clinical/medical visits where a patient was seen or treated."

The "Orders Only Encounter" entries don't involve the patient being seen. They are provider-only documentation. However, they do have dates of service and provider names, and they are part of the medical record. 

Looking at the January 27, 2025 entry: "Purpose: Lab Review. Recent lab results for HEME PROFILE + ELECT DIFF were reviewed and acknowledged by the provider." This is a clinical encounter where the provider reviewed lab results and made decisions (or decided not to make changes). This is part of the patient's medical care.

Looking at the January 7, 2025 entry: "New laboratory orders have been entered into the electronic health record for this patient." This is just placing orders, which is administrative. But it's documented as an encounter with a date of service and provider name.

I'll include both because they have provider names and dates of service, and they are part of the medical record. But I need to be careful about whether they are truly "visits."

Actually, looking at the format of the document, these "Orders Only Encounter" entries are listed under the provider's name and have a date of service. They are part of the patient's medical record. I'll include them.

Now, let me check if there are any other entries I might have missed. Looking at the document again, I see:

- The lab reports in EXHIBIT D are not visits themselves, they are results of visits.
- The imaging report in EXHIBIT F is from 2023, outside the date range.
- The billing and administrative sections (EXHIBIT E) should be excluded.
- The consent forms (EXHIBIT G) should be excluded.

So I believe I have all the visits.

Now, I need to make sure the formatting is correct. Let me check the instructions again:

"**Formatting:** Ensure **STRICT** markdown structure. Every bullet point must start on a NEW LINE. Do not output run-on paragraphs."

So I need to make sure each bullet point is on a new line.

Also, I need to check the field order again:
1. Type of Visit
2. Facility Name
3. Provider Name
4. Subjective/HPI/CC/Hospital Course
5. Objective/PE
6. Social
7. Labs
8. Surgery/Procedure
9. Imaging
10. Diagnoses
11. Plan/Assessment
12. MSS
13. Medication(s)
14. Referrals
15. Source References

I have all the fields in the correct order.

Now, I need to check if I need to include any empty fields. Looking at the instructions, it says "Under Heading 3, list fields using bullet points (`*`)." So I should include all fields, even if they're empty. But looking at the example, it only shows some fields. Let me check the example again:

"## Date of Medical Visit: 09/15/2022
### 09/15/2022
* **Type of Visit:** Orthopedics Clinic Note
* **Facility Name:** Willow Creek Medical Center
* **Provider Name:** Alistair Finch, MD
* **Subjective/HPI/CC/Hospital Course:** Patient presents with chronic right hip pain (8/10).
* **Diagnoses:** Avascular necrosis of right hip.
* **Source References:** (10E Page 27 of 43)"

The example only shows some fields. But the instructions say to follow the exact field order. So I should include all fields, even if they're empty. But looking at the example, it doesn't include all fields. Let me re-read the instructions:

"**Field Definitions (Exact Order)**
1. **Type of Visit:** (Primary Care, Orthopedic, Pulmonary, Hospital Admission, Exam, PT, etc)
2.  **Facility Name:** (If applicable. Do **NOT** use street addresses as Facility Names.)
3.  **Provider Name:** (If applicable.)
4.  **Subjective/HPI/CC/Hospital Course:** (Patient complaints, history)
5.  **Objective/PE:** (Vitals, physical exam findings)
6.  **Social:** (Flag Alcohol, Tobacco, or Substance/DAA use)
7.  **Labs:** (List significant abnormal results)
8.  **Surgery/Procedure:** (Specific procedures performed)
9.  **Imaging:** (MRI, X-ray, CT findings)
10.  **Diagnoses:** (Medical codes or named diagnoses)
11.  **Plan/Assessment:** (Treatment plan, discharge instructions)
12.  **MSS:** (Musculoskeletal specific findings)
13.  **Medication(s):** (Drugs prescribed)
14.  **Referrals:** (To PT, surgeons, etc.)
15.  **Source References:** (Include the exact source reference text found in the document, e.g., `(10E Page 27 of 43)` or `<!-- Source... -->`)"

So I should include all 15 fields in the exact order. But looking at the example, it doesn't include all fields. Maybe the example is just showing the most relevant fields, and I should include all fields that have information, and leave the others empty or omit them.

Actually, looking at the example again, it includes:
- Type of Visit
- Facility Name
- Provider Name
- Subjective/HPI/CC/Hospital Course
- Diagnoses
- Source References

It doesn't include:
- Objective/PE
- Social
- Labs
- Surgery/Procedure
- Imaging
- Plan/Assessment
- MSS
- Medication(s)
- Referrals

So maybe I should only include the fields that have information. But the instructions say "Follow the exact field order defined below." This is a bit ambiguous.

Let me re-read the instructions one more time:

"**Field Definitions (Exact Order)**
1. **Type of Visit:** (Primary Care, Orthopedic, Pulmonary, Hospital Admission, Exam, PT, etc)
2.  **Facility Name:** (If applicable. Do **NOT** use street addresses as Facility Names.)
3.  **Provider Name:** (If applicable.)
4.  **Subjective/HPI/CC/Hospital Course:** (Patient complaints, history)
5.  **Objective/PE:** (Vitals, physical exam findings)
6.  **Social:** (Flag Alcohol, Tobacco, or Substance/DAA use)
7.  **Labs:** (List significant abnormal results)
8.  **Surgery/Procedure:** (Specific procedures performed)
9.  **Imaging:** (MRI, X-ray, CT findings)
10.  **Diagnoses:** (Medical codes or named diagnoses)
11.  **Plan/Assessment:** (Treatment plan, discharge instructions)
12.  **MSS:** (Musculoskeletal specific findings)
13.  **Medication(s):** (Drugs prescribed)
14.  **Referrals:** (To PT, surgeons, etc.)
15.  **Source References:** (Include the exact source reference text found in the document, e.g., `(10E Page 27 of 43)` or `<!-- Source... -->`)"

I think I should include all fields that have information, and omit the fields that don't have information. But I need to maintain the order. So I'll include all fields that have information, in the correct order.

Actually, looking at the example again, it includes "Diagnoses" but not "Plan/Assessment" or "Medication(s)". So maybe I should include all fields that have information, and the example just happened to not include some fields.

Let me include all fields that have information, in the correct order. For fields that don't have information, I'll either omit them or include them with "[Not mentioned]" or "[Not applicable]".

Actually, looking at the instructions again: "Under Heading 3, list fields using bullet points (`*`)." So I should list all fields that have information. I'll include all fields that have information, and omit the ones that don't.

Wait, but the instructions also say "Follow the exact field order defined below." So I need to maintain the order, even if I omit some fields.

I'll include all fields that have information, in the correct order. For fields that don't have information, I'll omit them.

Actually, looking at the example again, it includes "Source References" at the end. So I should always include "Source References" as the last field.

Let me check my output again. I have all the fields that have information, in the correct order, and "Source References" as the last field. That looks correct.

Now, let me check if I need to add any additional information. Let me re-read the instructions one more time to make sure I haven't missed anything.

"**Output Rules (Hard Constraints)**
- Output **ONLY** the final “Medical Chronology” section.
- **Formatting:** Ensure **STRICT** markdown structure. Every bullet point must start on a NEW LINE. Do not output run-on paragraphs.
- Do NOT include: `<scratchpad>`, `analysis`, `reasoning`."

So I should only output the Medical Chronology section, and nothing else.

Now, let me check if I need to include any additional information from the lab reports. Looking at the lab reports in EXHIBIT D:

For May 2, 2024:
- Total Cholesterol: 220 H (ref <200)
- Triglycerides: 397 H (ref <150)
- HDL Cholesterol: 27 L (ref >40)
- VLDL Cholesterol Cal: 71 H (ref 5-40)
- LDL Cholesterol Calc: 122 H (ref <100)
- Hemoglobin A1C: 5.2 (normal)

For November 14, 2024:
- CBC results are all within normal limits

For January 27, 2025:
- CBC results are all within normal limits

I've included these in the Labs field.

Now, let me check if I need to include any other information. Looking at the document again, I see that the Chest X-Ray from 08/19/2023 is outside the date range. So I won't include it.

Also, I need to check if there are any other visits I might have missed. Let me look at the document one more time.

Actually, looking at the document again, I see that there's a "Telephone Encounter" on December 26, 2024, which I excluded. And there's a "Telephone Encounter" on December 27, 2024, which I included.

Let me also check if there are any other "Orders Only Encounter" entries. Looking at the document, there are two: January 7, 2025 and January 27, 2025. I've included both.

Now, I think I'm ready to output the final answer. Let me make sure the formatting is correct.

One more thing: I need to check if I should include the "Subjective/HPI/CC/Hospital Course" field for the "Orders Only Encounter" entries. For January 7, 2025, it's just placing orders, so there's no subjective. For January 27, 2025, it's lab review, so there's a brief description.

Let me check the format again. Looking at the example:

"* **Subjective/HPI/CC/Hospital Course:** Patient presents with chronic right hip pain (8/10)."

So I should use "Subjective/HPI/CC/Hospital Course" for all visits, even if it's brief.

For January 7, 2025, I'll use "Purpose: Lab orders" or something similar.

Actually, looking at the note: "New laboratory orders have been entered into the electronic health record for this patient." So I'll use that as the subjective.

For January 27, 2025: "Purpose: Lab Review. Recent lab results for HEME PROFILE + ELECT DIFF were reviewed and acknowledged by the provider."

That looks good.

Now, I'm ready to output the final answer.
</think>

## Date of Medical Visit: 05/02/2024
### 05/02/2024
* **Type of Visit:** Telemedicine / Behavioral Health Outpatient Clinic Follow-up
* **Facility Name:** Bridgewater Psychiatry Walnut Street
* **Provider Name:** Liu, Andrew K, MD
* **Subjective/HPI/CC/Hospital Course:** Return visit for medication management. Patient reports psychiatric symptoms stable since last appointment in November 2023. Currently unemployed but actively searching for job while taking classes to become an electrician. Sleep "ok" from around midnight until 12:00 or 1:00 PM. Denies recent changes in appetite but notes weight increase of 3-4 pounds. Exercise intermittent. Denies side effects from clozapine. Continues to endorse chronic delusions (thought broadcasting and thought insertion). Denies suicidal or homicidal ideation.
* **Objective/PE:** Mental Status Examination: Grooming appropriate. Eye contact fair. No psychomotor agitation/retardation, no choreoathetoid movements. Speech normal rate and rhythm. Mood "Ok". Affect blunted but intermittently reactive. Thought process linear and goal-directed. Content includes chronic delusions (thought broadcasting and thought insertion). Denies SI/HI. No auditory or visual hallucinations. Alert and oriented. Insight fair to limited, judgment fair. Weight 218 lbs. No EPS noted.
* **Social:** Out of work, pursuing vocational training in electrical work, resides with parents, interested in applying for SSI, primary social outlet online gaming.
* **Labs:** Weight 218 lbs (down from 231 lbs on 12/19/23). BMI 34.11 kg/m². Lipid Panel: Total Cholesterol 220 H, Triglycerides 397 H, HDL Cholesterol 27 L, VLDL Cholesterol 71 H, LDL Cholesterol 122 H. Hemoglobin A1C 5.2 (normal).
* **Diagnoses:** Schizophrenia, Paranoid type (F20.0); Hyperlipidemia; Long term current use of antipsychotic medication (Z79.899)
* **Plan/Assessment:** Continue clozapine 250 mg daily. Discussed potential benefits of Caplyta. Metabolic monitoring - orders for Hemoglobin A1c and Lipid Panel. Continue monthly CBC for ANC monitoring. Psychoeducation regarding lifestyle modifications for weight management. Follow up in 5-6 months.
* **Medication(s):** Clozapine 100 mg tablet, take 2.5 tablets by mouth daily; Omega-3 fatty acids 1000 mg capsule, take 2 capsules by mouth daily
* **Referrals:** Continue follow-up with PCP for hypertriglyceridemia; Follow up with metabolic specialist
* **Source References:** (Page 1 of 12)

## Date of Medical Visit: 11/14/2024
### 11/14/2024
* **Type of Visit:** Telemedicine / Psychiatry Follow Up
* **Facility Name:** Bridgewater Psychiatry Walnut Street
* **Provider Name:** Nair, Kavitha, MD
* **Subjective/HPI/CC/Hospital Course:** Return visit for medication management. Patient indicates period of stability, no significant changes to mental health or life circumstances. Continues to live at home with parents, enrolled in classes for electrician certification. Not currently employed. Sleep and mood unchanged. Occasional fleeting paranoid thoughts a couple times per month (feelings of being watched or monitored). Morning grogginess attributed to clozapine, denies other side effects. Explicitly denies SI/HI.
* **Objective/PE:** Mental Status Exam: Attention to hygiene and grooming appropriate. No abnormal motor activity. Cooperative and polite. Speech normal rate and rhythm. Mood "Fine". Affect mildly blunted but reactive. Thought process linear, organized, goal-directed. Mild paranoia noted, no other overt delusions or grandiosity. Denies auditory or visual hallucinations. Grossly oriented. Insight and judgment fair. Euthymic with slightly blunted affect. No AVH/delusions, no RIS, no SI/HI.
* **Social:** No problematic use of alcohol, cannabis, or nicotine.
* **Labs:** CBC within normal limits
* **Diagnoses:** Paranoid schizophrenia (CMS-HCC) F20.0; Long term current use of antipsychotic medication Z79.89
* **Plan/Assessment:** Continue clozapine 250 mg daily. Monitor response and tolerability. Order will be placed to obtain Clozapine level with next set of labs. Continue monthly ANC monitoring. Return in approximately 6 months. Psychoeducation provided. Encourage follow-up with PCP for general health maintenance. Risks and benefits of clozapine discussed. Not at acute risk. Check cloz level and continue to follow ANCs.
* **Medication(s):** Clozapine 250 mg tablet, take 2.5 tablets by mouth daily at bedtime for 180 days
* **Referrals:** None
* **Source References:** (Page 2 of 12)

## Date of Medical Visit: 12/17/2024
### 12/17/2024
* **Type of Visit:** Specialist Consultation - Follow-up for hyperlipidemia
* **Facility Name:** Bridgewater Heart and Vascular Center Briarwood
* **Provider Name:** Brennan, Thomas E, MD
* **Subjective/HPI/CC/Hospital Course:** Follow-up appointment stemming from original referral for detailed evaluation of hyperlipidemia (HL). Patient attended with mother.
* **Objective/PE:** [Not detailed in note]
* **Social:** [Not mentioned]
* **Labs:** [Not mentioned]
* **Diagnoses:** Combined hyperlipidemia; Class 1 obesity with serious comorbidity, BMI of 34.0 to 34.9 in an adult, unspecified obesity type
* **Plan/Assessment:** Recommendations provided for management of combined hyperlipidemia and obesity. Detailed discussion regarding dietary modification, importance of regular physical activity, potential future pharmacologic interventions if lifestyle changes not sufficient. Patient and mother verbalized understanding. Follow up as needed.
* **Medication(s):** [Not mentioned]
* **Referrals:** [Not mentioned]
* **Source References:** (Page 3 of 12)

## Date of Medical Visit: 12/27/2024
### 12/27/2024
* **Type of Visit:** Telephone Encounter
* **Facility Name:** Not specified
* **Provider Name:** Nair, Kavitha, MD
* **Subjective/HPI/CC/Hospital Course:** Telephone call received from patient's mother regarding recent laboratory results. Mother stated clozapine level came back with value slightly above 600.
* **Objective/PE:** [Not applicable]
* **Social:** [Not mentioned]
* **Labs:** Clozapine level slightly above 600
* **Diagnoses:** [Not mentioned]
* **Plan/Assessment:** Decision made to adjust medication. Daily dose of clozapine reduced from 250 mg to 225 mg. Plan to recheck clozapine level in one month, to be drawn at same time as next scheduled ANC. Mother verbalized understanding.
* **Medication(s):** Clozapine adjusted from 250 mg to 225 mg daily
* **Referrals:** [Not mentioned]
* **Source References:** (Page 2 of 12)

## Date of Medical Visit: 01/07/2025
### 01/07/2025
* **Type of Visit:** Orders Only Encounter
* **Facility Name:** Not specified
* **Provider Name:** Brennan, Thomas E, MD
* **Subjective/HPI/CC/Hospital Course:** New laboratory orders have been entered into the electronic health record for this patient.
* **Objective/PE:** [Not applicable]
* **Social:** [Not mentioned]
* **Labs:** [Not applicable - just ordering labs]
* **Diagnoses:** Primary Dx: Combined hyperlipidemia (E78.2); Secondary Dx: Insulin resistance (R73.03)
* **Plan/Assessment:** New laboratory orders entered: Lipid Panel w/ Reflex to Direct LDL, Insulin Fasting, Comprehensive Metabolic Panel. Order transmitted to preferred lab. Patient to complete prior to next follow-up.
* **Medication(s):** [Not mentioned]
* **Referrals:** [Not mentioned]
* **Source References:** (Page 3 of 12)

## Date of Medical Visit: 01/27/2025
### 01/27/2025
* **Type of Visit:** Orders Only Encounter - Lab Review
* **Facility Name:** Not specified
* **Provider Name:** Liu, Andrew K, MD
* **Subjective/HPI/CC/Hospital Course:** Purpose: Lab Review. Recent lab results for HEME PROFILE + ELECT DIFF were reviewed and acknowledged by the provider.
* **Objective/PE:** [Not applicable]
* **Social:** [Not mentioned]
* **Labs:** CBC within normal limits (WBC 4.4, RBC 5.47, Hemoglobin 15.5, Hematocrit 46.3, Platelets 194, ANC within normal limits)
* **Diagnoses:** Paranoid schizophrenia (CMS-HCC) [F20.0]; Long term current use of antipsychotic medication [Z79.899]
* **Plan/Assessment:** No additional clinical findings or changes to the plan of care documented for this date.
* **Medication(s):** [Not mentioned]
* **Referrals:** [Not mentioned]
* **Source References:** (Page 2 of 12)

## Date of Medical Visit: 02/10/2025
### 02/10/2025
* **Type of Visit:** Office Visit - Primary Care/Adolescent Medicine
* **Facility Name:** Bridgewater Adolescent and Young Adult Medicine Briarwood
* **Provider Name:** Reyes, Gabriela, MD
* **Subjective/HPI/CC/Hospital Course:** Chief complaint: Hair loss. Patient presents with primary concern of hair loss. Reports this has been occurring for some time. Attempted over-the-counter remedies including rosemary oil and topical minoxidil, no benefit. Family history of receding hair lines on mother's side and male pattern baldness on father's side.
* **Objective/PE:** Vitals: BP 111/76 mmHg, Pulse 84 bpm, Temp 97.6 F, Weight 227 lbs (103 kg), BMI 32.39 kg/m², SpO2 97% on room air. Physical Exam: Mouth/Throat - mucous membranes moist. Eyes - conjunctivae normal. Cardiovascular - heart rate and rhythm normal, heart sounds normal. Pulmonary - respiratory effort normal, breath sounds normal bilaterally. Skin - warm and dry, no rash. Scalp examination reveals receding hair line anteriorly, no bald patches. Neurological - no focal deficits. Psychiatric - mood and behavior normal.
* **Social:** Patient in process of applying for SSI, working with attorney Eleanor Caldwell.
* **Labs:** [Not mentioned]
* **Diagnoses:** Hair loss (L65.9) - likely androgenic alopecia; Hypertriglyceridemia (E78.1); Paranoid schizophrenia (F20.0)
* **Plan/Assessment:** Begin trial of oral minoxidil at 1.25 mg daily. Follow-up appointment in 2 months to evaluate response. Reinforced importance of lifestyle factors for hypertriglyceridemia (diet and exercise). Management of clozapine and monitoring to continue under Bridgewater psychiatry. Return in approximately 2 years for general follow-up and medication check, or sooner as needed.
* **Medication(s):** Oral minoxidil 1.25 mg daily
* **Referrals:** [Not mentioned]
* **Source References:** (Page 4 of 12)