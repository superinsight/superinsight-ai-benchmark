<scratchpad>
The user wants a chronological list of medical visits. I need to go through the provided text and identify all valid medical encounters based on the specified rules.

**Filtering Rules Checklist & Internal Analysis:**

1.  **Extraction & Inclusion Filtering:**
    *   **DOC ID: SUMMIT-NEURO-20250310-001 (Page 1):**
        *   Date: March 10, 2025
        *   Provider: Dr. Wendy Nakamura, MD
        *   Facility: Summit Neurology Associates
        *   Type: Clinic Visit Note (Neurology)
        *   Valid: Yes.
    *   **FAX TRANSMISSION REPORT (Page 2):**
        *   Date: 03/01/2025
        *   Type: Administrative (Prior Authorization Request)
        *   Valid: No (administrative, not a clinical visit).
    *   **DOC ID: SUMMIT-NEURO-20250310-002 (Page 2):**
        *   Date: March 10, 2025
        *   Provider: Dr. Elias Vance, MD (Radiologist)
        *   Facility: Summit Imaging Center
        *   Type: Imaging (MRI Brain)
        *   Valid: Yes.
    *   **DOC ID: Clearwater-Neuro-20250422-001 (Page 3):**
        *   Date: April 22, 2025
        *   Provider: Dr. Thomas Reeves, PhD, ABPP-CN
        *   Facility: Clearwater Neuropsychology Center
        *   Type: Neuropsychological Evaluation
        *   Valid: Yes.
    *   **DOC ID: ClearPath-PA-20250401-001 (Page 4):**
        *   Date: 04/01/2025 (Request date, not service date)
        *   Service Requested: Neuropsychological Testing (CPT codes: 96132, 96133, 96136, 96137)
        *   Date of Service(s): 04/22/2025 (This refers to the actual evaluation, which is already captured above).
        *   Type: Prior Authorization Request Form
        *   Valid: No (administrative, not a clinical visit).
    *   **DOC ID: SUMMIT-NEURO-20250605-001 (Page 5):**
        *   Date: 06/05/2025
        *   Provider: Dr. Wendy Nakamura, MD
        *   Facility: Summit Neurology Associates
        *   Type: Progress Note (Neurology Follow-up)
        *   Valid: Yes.
    *   **DOC ID: PT-Referral-20250515 (Page 6):**
        *   Date: 05/15/2025 (Referral date, not service date)
        *   Type: Referral Confirmation
        *   Valid: No (administrative, not a clinical visit).
    *   **DOC ID: PINEPT-20250728-001 (Page 7):**
        *   Date: July 28, 2025
        *   Provider: Sarah Mitchell, DPT
        *   Facility: Pinecrest Physical Therapy & Rehabilitation
        *   Type: Physical Therapy Initial Evaluation
        *   Valid: Yes.
    *   **DOC ID: PINEPT-20250728-002 (Page 8):**
        *   Date: 07/28/2025
        *   Provider: Sarah Mitchell, DPT
        *   Facility: Pinecrest Physical Therapy & Rehabilitation
        *   Type: Physical Therapy Initial Measurements (part of the initial evaluation, will be combined or noted as part of the PT eval). This is essentially the same visit as the previous one, just a different document for the same encounter. I will consolidate the information under the single PT evaluation.
        *   Valid: Yes, but will be merged with the previous entry for the same date/provider/facility.
    *   **DOC ID: Scheduling-Confirm-20250810 (Page 9):**
        *   Date: August 10, 2025 (Date sent)
        *   Type: Appointment Confirmation
        *   Valid: No (administrative, not a clinical visit).
    *   **DOC ID: SUMMIT-NEURO-20250915-001 (Page 10):**
        *   Date: September 15, 2025
        *   Provider: Dr. Wendy Nakamura, MD
        *   Facility: Summit Neurology Associates
        *   Type: Clinical Progress Note (Neurology Follow-up)
        *   Valid: Yes.
    *   **DOC ID: RIDGEVIEW-OM-20251020-001 (Page 11):**
        *   Date: October 20, 2025
        *   Provider: Dr. Frank Delgado, MD, MPH
        *   Facility: Ridgeview Occupational Medicine
        *   Type: Return-to-Work Evaluation
        *   Valid: Yes.
    *   **DOC ID: PATHFIND-INS-20251101-001 (Page 12):**
        *   Date: November 1, 2025 (Denial date)
        *   Service Date: 10/25/2025 (Vocational Rehabilitation Assessment)
        *   Provider: Pathways Vocational Services
        *   Type: Denial of Benefits (Administrative)
        *   Valid: No (administrative, not a clinical visit *by Jane Doe*). The service itself (Vocational Rehabilitation Assessment) is a clinical service, but the document is a denial, not a record of the visit itself. The prompt asks for "clinical/medical visits where a patient was seen or treated." This document is a denial *about* a service, not the service record. I will exclude this as it's an administrative denial, not a visit note.
    *   **DOC ID: SUMMIT-NEURO-20251210-001 (Page 13):**
        *   Date: December 10, 2025
        *   Provider: Dr. Wendy Nakamura, MD
        *   Facility: Summit Neurology Associates
        *   Type: Patient Clinic Visit Summary (Neurology Follow-up)
        *   Valid: Yes.
    *   **DOC ID: SUMMIT-NEURO-20251210-002 (Page 14):**
        *   Date: December 10, 2025
        *   Provider: Dr. Wendy Nakamura, MD
        *   Facility: Summit Neurology Associates
        *   Type: Prescription Order (part of the clinic visit)
        *   Valid: No (part of the clinic visit, not a separate visit). Information will be extracted and placed under the clinic visit.
    *   **DOC ID: RIDGEVIEW-OM-20260218-001 (Page 15):**
        *   Date: February 18, 2026
        *   Provider: Dr. Frank Delgado, MD, MPH
        *   Facility: Ridgeview Occupational Medicine
        *   Type: Final Work Capacity Evaluation
        *   Valid: Yes.
    *   **DOC ID: RECORDS-REQ-20260105 (Page 16):**
        *   Date: January 5, 2026
        *   Type: Medical Records Request
        *   Valid: No (legal/administrative).
    *   **DOC ID: PROVIDER-UPDATE-20250615 (Page 17):**
        *   Date: June 15, 2025
        *   Type: Provider Directory Update
        *   Valid: No (administrative list, explicitly excluded by rule).
    *   **DOC ID: SUMMIT-BILLING-20250325 (Page 18):**
        *   Date: 03/25/2025 (Billing date)
        *   Service Date: 03/10/2025 (Already captured)
        *   Type: Patient Billing Statement
        *   Valid: No (administrative/billing).
    *   **DOC ID: LAB-REPORT-20250310-001 (Page 19-20):**
        *   Date: March 10, 2025 (Collection/Report Date)
        *   Provider: Dr. Wendy Nakamura (Ordering Provider)
        *   Facility: Summit Clinical Laboratories
        *   Type: Laboratory Report
        *   Valid: Yes. This is a separate service from the neurology visit, even if on the same day.

2.  **Sorting & Deduplication:**
    *   March 10, 2025: Neurology Clinic Visit (Nakamura)
    *   March 10, 2025: MRI Brain (Vance)
    *   March 10, 2025: Lab Report (Nakamura/Summit Clinical Labs)
    *   April 22, 2025: Neuropsychological Evaluation (Reeves)
    *   June 05, 2025: Neurology Progress Note (Nakamura)
    *   July 28, 2025: Physical Therapy Initial Evaluation (Mitchell)
    *   September 15, 2025: Neurology Clinical Progress Note (Nakamura)
    *   October 20, 2025: Return-to-Work Evaluation (Delgado)
    *   December 10, 2025: Neurology Clinic Visit Summary (Nakamura)
    *   February 18, 2026: Final Work Capacity Evaluation (Delgado)

    All distinct visits are identified and will be sorted chronologically. Multiple visits on the same day will be listed as separate `###` entries.

3.  **Content Extraction for each valid visit:**

    *   **03/10/2025 - Summit Neurology Associates (Dr. Nakamura)**
        *   Type of Visit: Clinic Visit Note
        *   Facility Name: Summit Neurology Associates
        *   Provider Name: Dr. Wendy Nakamura, MD
        *   Subjective/HPI/CC/Hospital Course: Persistent head pain and difficulty with concentration for 6 months, daily head discomfort (5-7/10 pressure sensation, bilateral forehead), light sensitivity, occasional nausea. Cognitive decline (focus, word-finding, memory) since MVA 8 months prior. No prior headache history.
        *   Objective/PE: Alert and oriented, CN II-XII intact, motor strength 5/5, sensory intact, cerebellar functions normal, Romberg negative. MMSE 28/30 (errors in delayed recall and serial sevens).
        *   Diagnoses: Post-traumatic headache syndrome, Post-concussion syndrome with observed cognitive difficulties, Migraine without aura.
        *   Plan/Assessment: Neuropsychological evaluation advised, maintain headache diary, MRA scan considered if no improvement, follow-up in 6 weeks.
        *   Medication(s): Topiramate (initiated 25mg QD, increase to 50mg BID), Sumatriptan (50mg PRN for acute migraine).
        *   Referrals: Neuropsychological testing.
        *   Source References: (DOC ID: SUMMIT-NEURO-20250310-001 | PAGE 1 of 42)

    *   **03/10/2025 - Summit Imaging Center (Dr. Vance)**
        *   Type of Visit: Imaging (MRI Brain W/ and W/O Contrast)
        *   Facility Name: Summit Imaging Center
        *   Provider Name: Dr. Elias Vance, MD
        *   Subjective/HPI/CC/Hospital Course: Headaches, cognitive impairment following MVA.
        *   Imaging: No acute infarct, hemorrhage, or mass lesion. Ventricular system, sulci, gyri normal. Scattered small, nonspecific T2/FLAIR hyperintensities in bilateral frontal lobes (non-enhancing, consistent with prior trauma or chronic microvascular changes). No significant stenosis, aneurysm, or AVM. Unremarkable orbits/sinuses/mastoids. Cerebellum and brainstem normal. No abnormal intracranial enhancement.
        *   Diagnoses: No acute intracranial pathology. Small, nonspecific white matter hyperintensities in bilateral frontal lobes (etiology non-specific, could be post-traumatic). No mass effect or midline shift.
        *   Source References: (DOC ID: SUMMIT-NEURO-20250310-002 | PAGE 2 of 42)

    *   **03/10/2025 - Summit Clinical Laboratories (Dr. Nakamura)**
        *   Type of Visit: Laboratory Report
        *   Facility Name: Summit Clinical Laboratories
        *   Provider Name: Dr. Wendy Nakamura (Ordering Provider)
        *   Labs: All values within normal limits for CBC, CMP, and TSH.
        *   Source References: (DOC ID: LAB-REPORT-20250310-001 | PAGE 19 of 42)

    *   **04/22/2025 - Clearwater Neuropsychology Center (Dr. Reeves)**
        *   Type of Visit: Comprehensive Neuropsychological Evaluation
        *   Facility Name: Clearwater Neuropsychology Center
        *   Provider Name: Dr. Thomas Reeves, PhD, ABPP-CN
        *   Subjective/HPI/CC/Hospital Course: Assessment of persistent cognitive difficulties (attention, memory, executive functions) following MVA 8 months prior. No prior cognitive problems. Not employed, lives independently, no ADL difficulties.
        *   Objective/PE: Tests administered: WAIS-IV, WMS-IV, Trail Making Test, Stroop, WCST, BNT, CVLT-II, RCFT, Conners CPT-3, MMPI-2-RF, TOMM. Processing Speed (low average SS 85), Attention/Concentration (borderline SS 78), Verbal Memory (low average SS 82), Visual Memory (average SS 95), Executive Function (low average SS 84), Language (average SS 98). TOMM passed (valid effort). MMPI-2-RF elevated somatic complaints/diminished positive emotions, no symptom over-reporting.
        *   Diagnoses: Mild neurocognitive disorder directly attributable to traumatic brain injury, Post-concussion syndrome.
        *   Plan/Assessment: Cognitive rehabilitation therapy (2x/week), vocational rehabilitation assessment, accommodations for return-to-work (reduced screen exposure, written task lists, quiet environment), re-evaluation in 6 months.
        *   Source References: (DOC ID: Clearwater-Neuro-20250422-001 | PAGE 3 of 42)

    *   **06/05/2025 - Summit Neurology Associates (Dr. Nakamura)**
        *   Type of Visit: Progress Note
        *   Facility Name: Summit Neurology Associates
        *   Provider Name: Dr. Wendy Nakamura, MD
        *   Subjective/HPI/CC/Hospital Course: Improved headache frequency (daily to 3-4x/week) since starting Topiramate. Cognitive symptoms persist but slight improvement with cognitive rehabilitation. Tingling in fingers bilaterally (potential Topiramate side effect).
        *   Objective/PE: Intact CN II-XII, motor strength 5/5 all extremities. Reduced perception of pinprick stimuli at distal fingertips bilaterally. MMSE 29/30.
        *   Diagnoses: Post-traumatic headache (improving), Post-concussion cognitive impairment (ongoing), Paresthesias induced by Topiramate.
        *   Plan/Assessment: Continue cognitive rehabilitation. Monitor paresthesias after Topiramate dosage reduction. Consider Propranolol if headaches worsen. Follow-up in 8 weeks.
        *   Medication(s): Topiramate (reduced to 25mg BID due to paresthesias), Sumatriptan (PRN), Magnesium Glycinate (400mg QD added for migraine prevention).
        *   Source References: (DOC ID: SUMMIT-NEURO-20250605-001 | PAGE 5 of 42)

    *   **07/28/2025 - Pinecrest Physical Therapy & Rehabilitation (Sarah Mitchell)**
        *   Type of Visit: Initial Physical Therapy Evaluation
        *   Facility Name: Pinecrest Physical Therapy & Rehabilitation
        *   Provider Name: Sarah Mitchell, DPT
        *   Subjective/HPI/CC/Hospital Course: Neck pain and dizziness after MVA. Neck stiffness, dizziness with quick head movements. Participating in cognitive rehabilitation.
        *   Objective/PE: Cervical ROM reduced (Flexion 35/50, Extension 40/60, Rotation R 55/80, L 60/80, Lateral Flexion R 30/45, L 35/45). Tenderness in upper trapezius and suboccipital region bilaterally. Dix-Hallpike and BPPV screen negative. Mild dizziness with rapid horizontal head turns. Single Leg Stance R 15s, L 12s (norm >30s). DGI 20/24 (mild impairment).
        *   Diagnoses: Cervicalgia, Cervicogenic dizziness, Vestibular dysfunction (post-concussion type).
        *   Plan/Assessment: PT 2x/week for 8 weeks. Interventions: Vestibular rehab, cervical stretching/strengthening, gaze stabilization, balance training. Goals: Improve cervical ROM, decrease dizziness, enhance balance, return to prior activity.
        *   MSS: Reduced cervical ROM, tenderness in upper trapezius and suboccipital region.
        *   Source References: (DOC ID: PINEPT-20250728-001 | PAGE 7 of 42), (DOC ID: PINEPT-20250728-002 | PAGE 8 of 42)

    *   **09/15/2025 - Summit Neurology Associates (Dr. Nakamura)**
        *   Type of Visit: Clinical Progress Note
        *   Facility Name: Summit Neurology Associates
        *   Provider Name: Dr. Wendy Nakamura, MD
        *   Subjective/HPI/CC/Hospital Course: Further reduction in headache frequency (1-2x/week). Tingling sensations resolved. Significant improvement in dizziness (attributed to vestibular PT). Cognitive function feels better overall. Plans to attempt part-time work within next month.
        *   Objective/PE: CN II-XII normal. Motor strength 5/5 all extremities. Sensory examination normal. Cervical ROM improved. No nystagmus.
        *   Diagnoses: Post-traumatic headache (significantly improved), Post-concussion syndrome (ongoing improvement), Cervicogenic dizziness (resolved).
        *   Plan/Assessment: Continue current medication. Consider gradual Topiramate tapering if headaches controlled. Support return to part-time employment with accommodations. Follow-up in 3 months.
        *   Source References: (DOC ID: SUMMIT-NEURO-20250915-001 | PAGE 10 of 42)

    *   **10/20/2025 - Ridgeview Occupational Medicine (Dr. Delgado)**
        *   Type of Visit: Return-to-Work Evaluation
        *   Facility Name: Ridgeview Occupational Medicine
        *   Provider Name: Dr. Frank Delgado, MD, MPH
        *   Subjective/HPI/CC/Hospital Course: Assessment for fitness for duty for planned return to part-time office work. Headaches and cognitive abilities improved. Concerns about screen time tolerance and multitasking capacity.
        *   Objective/PE: Physical exam unremarkable. Neurological exam normal. Sitting tolerance: 2 hours continuous, then 10 min break. Sustained attention: adequate for simple tasks, decreased for complex. Screen tolerance: headache after ~90 min continuous screen exposure.
        *   Diagnoses: Post-concussion syndrome (recovery phase), Fitness for modified duty.
        *   Plan/Assessment: Cleared for part-time work (4 hours/day) with restrictions: frequent screen breaks (every 60-90 min), written instructions for tasks, quiet work environment, no driving for work. Re-evaluation in 8 weeks.
        *   Source References: (DOC ID: RIDGEVIEW-OM-20251020-001 | PAGE 11 of 42)

    *   **12/10/2025 - Summit Neurology Associates (Dr. Nakamura)**
        *   Type of Visit: Patient Clinic Visit Summary
        *   Facility Name: Summit Neurology Associates
        *   Provider Name: Dr. Wendy Nakamura, MD
        *   Subjective/HPI/CC/Hospital Course: Employed part-time for 6 weeks. Headaches infrequent (~1x/week), mild intensity. No dizziness. Cognitive function adequate for current workload, some difficulty with longer meetings. Tolerates Topiramate 25mg BID well.
        *   Objective/PE: Physical and neurological exam normal. MMSE 30/30.
        *   Diagnoses: Post-traumatic headache disorder (nearing resolution), Post-concussion cognitive impairment (mild residual symptoms).
        *   Plan/Assessment: Gradual taper of Topiramate (25mg QD for 2 weeks, then 25mg QOD for 2 weeks, then discontinue). Continue Magnesium Glycinate 400mg daily. Recommend follow-up with occupational medicine for full duty assessment. Consider repeating neuropsychological testing in ~6 months.
        *   Medication(s): Topiramate (tapering initiated), Magnesium Glycinate (continue), Sumatriptan (continue PRN, from previous prescription).
        *   Source References: (DOC ID: SUMMIT-NEURO-20251210-001 | PAGE 13 of 42), (DOC ID: SUMMIT-NEURO-20251210-002 | PAGE 14 of 42)

    *   **02/18/2026 - Ridgeview Occupational Medicine (Dr. Delgado)**
        *   Type of Visit: Final Work Capacity Evaluation
        *   Facility Name: Ridgeview Occupational Medicine
        *   Provider Name: Dr. Frank Delgado, MD, MPH
        *   Subjective/HPI/CC/Hospital Course: Re-evaluation for full-time employment. Worked part-time (4 hours/day) for 4 months without issues. Headaches rare (2-3x/month). Off Topiramate for 4 weeks. Denies current dizziness or cognitive complaints at present workload.
        *   Objective/PE: Physical exam normal. Sitting tolerance: 4+ hours with standard breaks. Screen tolerance: >3 hours. Attention: sustained and divided attention within normal limits.
        *   Diagnoses: Post-concussion syndrome (nearly resolved), Cleared for full-time duty with minimal restrictions.
        *   Plan/Assessment: Cleared for full-time work (8 hours/day). Recommendations: ergonomic workstation, screen breaks every 2 hours, no restriction on driving for work. Final follow-up with neurologist recommended.
        *   Source References: (DOC ID: RIDGEVIEW-OM-20260218-001 | PAGE 15 of 42)

Confidence Score: 5/5 - All rules applied, all relevant data extracted and formatted.
Strategizing complete. I will now generate the response based on this analysis.## Date of Medical Visit: 03/10/2025
### 03/10/2025
*   **Type of Visit:** Clinic Visit Note
*   **Facility Name:** Summit Neurology Associates
*   **Provider Name:** Dr. Wendy Nakamura, MD
*   **Subjective/HPI/CC/Hospital Course:** Patient presents with persistent head pain and difficulty with concentration. Describes daily head discomfort for approximately six months, characterized as a pressure sensation affecting both sides of her forehead, intensity 5-7/10. Associated symptoms include sensitivity to light and occasional nausea. Reports decline in cognitive abilities (focus, word-finding, remembering recent information) since a motor vehicle accident eight months prior. No history of headaches prior to the accident.
*   **Objective/PE:** Mental status alert and oriented. Cranial nerves II-XII intact. Motor strength 5/5 symmetrical. Sensory perception intact. Cerebellar functions normal. Romberg's test negative. MMSE 28/30 (deducted for errors in delayed recall and serial sevens subtraction).
*   **Diagnoses:** Post-traumatic headache syndrome; Post-concussion syndrome with observed cognitive difficulties; Migraine without aura.
*   **Plan/Assessment:** Comprehensive neuropsychological evaluation strongly advised. Patient instructed to maintain a detailed headache diary for four weeks. MRA scan considered if headaches do not improve. Follow-up scheduled for six weeks.
*   **Medication(s):** Topiramate (initiated 25mg QD, increase to 50mg BID as tolerated); Sumatriptan (50mg PRN for acute migraine).
*   **Referrals:** Neuropsychological testing.
*   **Source References:** (DOC ID: SUMMIT-NEURO-20250310-001 | PAGE 1 of 42)

### 03/10/2025
*   **Type of Visit:** Imaging (MRI Brain W/ and W/O Contrast)
*   **Facility Name:** Summit Imaging Center
*   **Provider Name:** Dr. Elias Vance, MD
*   **Subjective/HPI/CC/Hospital Course:** Clinical Indication: Headaches, cognitive impairment following MVA.
*   **Imaging:** No evidence of acute infarct, hemorrhage, or mass lesion. Ventricular system, sulci, and gyri appear normal for age. No hydrocephalus or significant atrophy. Scattered small, nonspecific areas of T2/FLAIR hyperintensity within bilateral frontal lobes (non-enhancing, could be consistent with sequelae of prior trauma or chronic microvascular changes). No evidence of significant stenosis, aneurysm, or arteriovenous malformation. Orbits/sinuses/mastoids unremarkable. Cerebellum and brainstem appear normal. No abnormal intracranial enhancement.
*   **Diagnoses:** No acute intracranial pathology. Small, nonspecific white matter hyperintensities in the bilateral frontal lobes, etiology non-specific but could represent post-traumatic changes. No evidence of mass effect or midline shift.
*   **Source References:** (DOC ID: SUMMIT-NEURO-20250310-002 | PAGE 2 of 42)

### 03/10/2025
*   **Type of Visit:** Laboratory Report
*   **Facility Name:** Summit Clinical Laboratories
*   **Provider Name:** Dr. Wendy Nakamura (Ordering Provider)
*   **Labs:** Complete Blood Count (CBC) - all values within normal limits. Comprehensive Metabolic Panel (CMP) - all values within normal limits. Thyroid Stimulating Hormone (TSH) - 2.15 mIU/L (within normal limits).
*   **Source References:** (DOC ID: LAB-REPORT-20250310-001 | PAGE 19 of 42)

## Date of Medical Visit: 04/22/2025
### 04/22/2025
*   **Type of Visit:** Comprehensive Neuropsychological Evaluation
*   **Facility Name:** Clearwater Neuropsychology Center
*   **Provider Name:** Dr. Thomas Reeves, PhD, ABPP-CN
*   **Subjective/HPI/CC/Hospital Course:** Patient underwent assessment for ongoing cognitive complaints (attention, memory, executive functions) attributed to a motor vehicle collision eight months prior. Patient asserts no cognitive problems prior to the accident. Not employed, resides independently, no difficulties managing ADLs.
*   **Objective/PE:** Tests administered: WAIS-IV, WMS-IV, Trail Making Test, Stroop Color-Word Test, Wisconsin Card Sorting Test, Boston Naming Test, California Verbal Learning Test, Rey Complex Figure Test, Conners CPT-3, MMPI-2-RF, Test of Memory Malingering (TOMM). Processing Speed (low average SS 85), Attention and Concentration (borderline SS 78), Verbal Memory (low average SS 82), Visual Memory (average SS 95), Executive Function (low average SS 84), Language (average SS 98). TOMM passed, suggesting valid effort. MMPI-2-RF showed elevated scores on somatic complaints and diminished positive emotions, no indication of symptom over-reporting.
*   **Diagnoses:** Mild neurocognitive disorder, directly attributable to traumatic brain injury; Post-concussion syndrome.
*   **Plan/Assessment:** Test results consistent with mild neurocognitive disorder from TBI. Referral for cognitive rehabilitation therapy (2x/week) recommended. Vocational rehabilitation assessment should be pursued. Accommodations for potential return-to-work: reduced screen exposure, written task lists, quiet work environment. Re-evaluation of cognitive functioning suggested in approximately six months.
*   **Source References:** (DOC ID: Clearwater-Neuro-20250422-001 | PAGE 3 of 42)

## Date of Medical Visit: 06/05/2025
### 06/05/2025
*   **Type of Visit:** Progress Note
*   **Facility Name:** Summit Neurology Associates
*   **Provider Name:** Dr. Wendy Nakamura, MD
*   **Subjective/HPI/CC/Hospital Course:** Patient reports improvement in headache frequency (daily to 3-4x/week) since starting Topiramate. Cognitive symptoms persist but slight improvement noted since engaging in cognitive rehabilitation. Describes tingling sensations in fingers bilaterally, recognized as a potential side effect of Topiramate.
*   **Objective/PE:** Intact cranial nerves (II through XII). Motor strength 5/5 in all extremities. Sensory examination showed reduced perception of pinprick stimuli at distal fingertips bilaterally. Mini-Mental Status Examination score 29/30.
*   **Diagnoses:** Post-traumatic headache, showing signs of improvement; Post-concussion cognitive impairment, ongoing; Paresthesias induced by Topiramate.
*   **Plan/Assessment:** Continue cognitive rehabilitation sessions. Monitor resolution of paresthesias following Topiramate dosage reduction. If headaches worsen, consider switching to Propranolol. Return to clinic for follow-up in eight weeks.
*   **Medication(s):** Topiramate (dosage adjusted from 50mg BID to 25mg BID due to paresthesias); Sumatriptan (continues PRN); Magnesium Glycinate (400mg QD added for migraine prevention).
*   **Source References:** (DOC ID: SUMMIT-NEURO-20250605-001 | PAGE 5 of 42)

## Date of Medical Visit: 07/28/2025
### 07/28/2025
*   **Type of Visit:** Initial Physical Therapy Evaluation
*   **Facility Name:** Pinecrest Physical Therapy & Rehabilitation
*   **Provider Name:** Sarah Mitchell, DPT
*   **Subjective/HPI/CC/Hospital Course:** Initial physical therapy assessment for complaints of neck pain and dizziness experienced after a motor vehicle accident. Reports stiffness in her neck and episodes of dizziness, particularly with quick head movements. Notes participation in cognitive rehabilitation therapy.
*   **Objective/PE:** Cervical ROM: Flexion 35/50, Extension 40/60, Rotation R 55/80, L 60/80, Lateral Flexion R 30/45, L 35/45. Palpation: Tenderness bilaterally in upper trapezius and suboccipital region. Vestibular Assessment: Dix-Hallpike and BPPV screen negative. Reported mild dizziness upon rapid horizontal head turns. Balance Assessment: Single Leg Stance R 15s, L 12s (norm >30s). Dynamic Gait Index (DGI): 20/24 (mild impairment).
*   **Diagnoses:** Cervicalgia (neck pain); Cervicogenic dizziness; Vestibular dysfunction, post-concussion type.
*   **Plan/Assessment:** Plan of care: PT 2x/week for 8 weeks. Interventions: Vestibular rehabilitation exercises, stretching and strengthening for cervical spine, gaze stabilization techniques, balance training. Goals: Improve cervical ROM, decrease dizziness, enhance balance, facilitate return to prior activity level.
*   **MSS:** Reduced cervical range of motion, tenderness in upper trapezius and suboccipital region.
*   **Source References:** (DOC ID: PINEPT-20250728-001 | PAGE 7 of 42), (DOC ID: PINEPT-20250728-002 | PAGE 8 of 42)

## Date of Medical Visit: 09/15/2025
### 09/15/2025
*   **Type of Visit:** Clinical Progress Note
*   **Facility Name:** Summit Neurology Associates
*   **Provider Name:** Dr. Wendy Nakamura, MD
*   **Subjective/HPI/CC/Hospital Course:** Patient reports further reduction in headache frequency, now 1-2x/week. Tingling sensations in fingers completely resolved since dosage reduction. Significant improvement in dizziness, attributed to vestibular physical therapy. Cognitive function feels better overall. Indicates plans to attempt returning to part-time work within the next month.
*   **Objective/PE:** Cranial nerve examination (II-XII) normal. Motor strength 5/5 in all extremities. Sensory examination within normal limits. Cervical range of motion showed improvement. No nystagmus observed.
*   **Diagnoses:** Post-traumatic headache, significantly improved; Post-concussion syndrome, showing ongoing improvement; Cervicogenic dizziness, now resolved.
*   **Plan/Assessment:** Continue with current medication regimen. Consider gradual tapering of Topiramate if headaches remain well-controlled. Support patient's planned return to part-time employment, emphasizing appropriate accommodations. Follow-up appointment scheduled in three months.
*   **Source References:** (DOC ID: SUMMIT-NEURO-20250915-001 | PAGE 10 of 42)

## Date of Medical Visit: 10/20/2025
### 10/20/2025
*   **Type of Visit:** Return-to-Work Evaluation
*   **Facility Name:** Ridgeview Occupational Medicine
*   **Provider Name:** Dr. Frank Delgado, MD, MPH
*   **Subjective/HPI/CC/Hospital Course:** Assessment of fitness for duty for a planned return to part-time office work. Patient, previously a data analyst, states headaches and cognitive abilities have shown improvement. Primary concerns are tolerance for screen time and capacity for multitasking.
*   **Objective/PE:** Physical examination unremarkable. Neurological examination normal. Functional Capacity Assessment: Sitting tolerance 2 hours continuous before 10-minute break. Sustained attention adequate for simple tasks, decreased for complex. Screen tolerance: onset of headache after ~90 minutes continuous screen exposure.
*   **Diagnoses:** Post-concussion syndrome, in a recovery phase; Fitness for modified duty.
*   **Plan/Assessment:** Cleared for part-time work (4 hours/day) with restrictions: frequent breaks from screen use (every 60-90 minutes), provision of written instructions for tasks, quiet work environment, no driving for work-related purposes. Re-evaluation advised in eight weeks.
*   **Source References:** (DOC ID: RIDGEVIEW-OM-20251020-001 | PAGE 11 of 42)

## Date of Medical Visit: 12/10/2025
### 12/10/2025
*   **Type of Visit:** Patient Clinic Visit Summary
*   **Facility Name:** Summit Neurology Associates
*   **Provider Name:** Dr. Wendy Nakamura, MD
*   **Subjective/HPI/CC/Hospital Course:** Patient reports having been employed part-time for six weeks. Headaches now infrequent (~1x/week), mild intensity. No dizziness. Cognitive function generally adequate for current workload, though some difficulty with longer meetings. Tolerates Topiramate 25mg BID well.
*   **Objective/PE:** Physical and neurological examination findings normal. Mini-Mental Status Examination score 30/30.
*   **Diagnoses:** Post-traumatic headache disorder, nearing resolution; Post-concussion cognitive impairment, with mild residual symptoms.
*   **Plan/Assessment:** Initiate gradual taper of Topiramate (25mg QD for 2 weeks, then 25mg QOD for 2 weeks, then discontinue). Continue Magnesium Glycinate 400mg daily. Recommend follow-up with occupational medicine for assessment of full duty work. Consider repeating neuropsychological testing in approximately six months.
*   **Medication(s):** Topiramate (tapering initiated); Magnesium Glycinate (continue 400mg daily); Sumatriptan (continue PRN, as previously prescribed).
*   **Source References:** (DOC ID: SUMMIT-NEURO-20251210-001 | PAGE 13 of 42), (DOC ID: SUMMIT-NEURO-20251210-002 | PAGE 14 of 42)

## Date of Medical Visit: 02/18/2026
### 02/18/2026
*   **Type of Visit:** Final Work Capacity Evaluation
*   **Facility Name:** Ridgeview Occupational Medicine
*   **Provider Name:** Dr. Frank Delgado, MD, MPH
*   **Subjective/HPI/CC/Hospital Course:** Re-assessment for progression to full-time work duty. Patient reports working part-time (4 hours/day) for the past four months without significant issues. Headaches now rare (2-3x/month). Off Topiramate medication for four weeks. Denies any current dizziness or cognitive complaints at her present workload.
*   **Objective/PE:** Physical exam entirely normal. Functional Capacity Assessment: Sitting tolerance for four or more hours with standard breaks. Screen tolerance exceeding three hours. Screening assessments for sustained and divided attention within normal limits.
*   **Diagnoses:** Post-concussion syndrome, nearly resolved; Cleared for full-time duty with minimal restrictions.
*   **Plan/Assessment:** Cleared for full-time work (8 hours/day). Minimal restrictions/recommendations: ergonomic workstation setup, screen breaks every two hours, no restriction on driving for work purposes. Final follow-up with neurologist recommended.
*   **Source References:** (DOC ID: RIDGEVIEW-OM-20260218-001 | PAGE 15 of 42)