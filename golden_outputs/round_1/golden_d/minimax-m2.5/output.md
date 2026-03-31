<think>Let me carefully analyze this medical document to extract all valid clinical visits according to the specified criteria.

First, I need to identify all potential encounters and then filter based on the rules:

1. **Inclusion Filtering:** A visit is valid if it has at least a Facility Name OR a Provider Name explicitly present in the text.

2. **Scope Filtering:**
   - Discard all legal events (depositions, legal reviews).
   - Discard "Provider Lists", "Directories", "Staff Updates", "Medical Provider List Updates", or "Summaries of Treating Providers".
   - Discard non-medical events (billing, admin).

3. **Sorting:** Sort valid visits chronologically.

4. **Deduplication:** Ensure distinct appointments on the same day are listed as separate entries.

Let me go through the document systematically:

**Exhibit 1F: Lakewood Family Medicine, Dr. Anita Patel, MD**

1. **2020-06-12** - Initial evaluation for back condition
   - Facility: Lakewood Family Medicine
   - Provider: Dr. Anita Patel, MD
   - Valid visit ✓

2. **November 10, 2020** - Follow-up after epidural injections
   - Facility: Lakewood Family Medicine
   - Provider: Dr. Anita Patel, MD
   - Valid visit ✓

3. **14-Jul-21** - Annual physical
   - Facility: Lakewood Family Medicine
   - Provider: Dr. Anita Patel, MD
   - Valid visit ✓

4. **2022-02-17** - Management of metabolic and mental health
   - Facility: Lakewood Family Medicine
   - Provider: Dr. Anita Patel, MD
   - Valid visit ✓

5. **2023-08-22** - Follow-up
   - Facility: Lakewood Family Medicine
   - Provider: Dr. Anita Patel, MD
   - Valid visit ✓

**Exhibit 2F: Tri-County Orthopedic Associates, Dr. Marcus Greene, DO**

6. **2020-08-03** - Orthopedic consultation
   - Facility: Tri-County Orthopedic Associates
   - Provider: Dr. Marcus Greene, DO
   - Valid visit ✓

7. **March 22, 2021** - Orthopedic follow-up
   - Facility: Tri-County Orthopedic Associates
   - Provider: Dr. Marcus Greene, DO
   - Valid visit ✓

**Exhibit 3F: Riverside Pain Management Center, Dr. Helen Cho, MD**

8. **2020-09-15** - First epidural steroid injection
   - Facility: Riverside Pain Management Center
   - Provider: Dr. Helen Cho, MD
   - Valid visit ✓

9. **2020-10-01** - Second injection
   - Facility: Riverside Pain Management Center
   - Provider: Dr. Helen Cho, MD
   - Valid visit ✓

10. **2022-10-25** - Pain management follow-up
    - Facility: Riverside Pain Management Center
    - Provider: Dr. Helen Cho, MD
    - Valid visit ✓

11. **January 18, 2023** - Medial branch block
    - Facility: Riverside Pain Management Center
    - Provider: Dr. Helen Cho, MD
    - Valid visit ✓

12. **2023-04-05** - Radiofrequency ablation
    - Facility: Riverside Pain Management Center
    - Provider: Dr. Helen Cho, MD
    - Valid visit ✓

**Exhibit 4F: Bayview Behavioral Health, Dr. Sandra Kim, PsyD**

13. **November 2nd, 2021** - Initial psychiatric evaluation
    - Facility: Bayview Behavioral Health
    - Provider: Dr. Sandra Kim, PsyD
    - Valid visit ✓

**Exhibit 5F: Heartland Cardiology Group, Dr. James Whitfield, MD**

14. **June 8, 2022** - Cardiology consultation
    - Facility: Heartland Cardiology Group
    - Provider: Dr. James Whitfield, MD
    - Valid visit ✓

**Exhibit 10F: Independent Medical Examination Office, Dr. Robert Hargrove, MD**

15. **2024-01-10** - Independent consultative examination
    - Facility: Independent Medical Examination Office
    - Provider: Dr. Robert Hargrove, MD
    - Valid visit ✓

Now I'll organize these visits chronologically, ensuring each entry is properly formatted with the required details. The chronology spans from June 2020 through January 2024, covering multiple medical specialties and facilities.

**2020-06-12** - Lakewood Family Medicine - Dr. Anita Patel
**2020-08-03** - Tri-County Orthopedic Associates - Dr. Marcus Greene
**2020-09-15** - Riverside Pain Management Center - Dr. Helen Cho
**2020-10-01** - Riverside Pain Management Center - Dr. Helen Cho
**2020-11-10** - Lakewood Family Medicine - Dr. Anita Patel
**2021-03-22** - Tri-County Orthopedic Associates - Dr. Marcus Greene
**2021-07-14** - Lakewood Family Medicine - Dr. Anita Patel
**2021-11-02** - Bayview Behavioral Health - Dr. Sandra Kim
**2022-02-17** - Lakewood Family Medicine - Dr. Anita Patel
**2022-06-08** - Heartland Cardiology Group - Dr. James Whitfield
**2022-10-25** - Riverside Pain Management Center - Dr. Helen Cho
**2023-01-18** - Riverside Pain Management Center - Dr. Helen Cho
**2023-04-05** - Riverside Pain Management Center - Dr. Helen Cho
**2023-08-22** - Lakewood Family Medicine - Dr. Anita Patel
**2024-01-10** - Independent Medical Examination Office - Dr. Robert Hargrove

I need to verify whether the Addendum entries are duplicative or additional. The 7/14/2021 entry appears to match the earlier July 14, 2021 visit, and 11/2/2021 corresponds to the psychiatric evaluation from that same date. The 1/18/2023 entry also aligns with the medial branch block documented in the main text. Since these are already captured in the chronological list, I won't treat them as separate encounters.

Now I'm extracting the detailed clinical documentation from each visit to populate the structured format, starting with the initial evaluation at Lakewood Family Medicine in June 2020.

**2020-06-12** - Lakewood Family Medicine - Dr. Anita Patel
- Primary Care visit for back pain
- Subjective: 3-month history of low back pain radiating down left leg, 6/10 pain, exacerbated by sitting
- Objective: BP 132/84, HR 78, Wt 198 lbs, limited lumbar ROM, positive straight leg raise left at 40°, tenderness L4-L5 paraspinal, DTR 2+/2+ patella, 1+/2+ Achilles
- Assessment: Lumbar radiculopathy, lumbar disc degeneration
- Plan: Naproxen 500mg BID, Cyclobenzaprine 10mg HS, referral to orthopedic spine specialist
- Source: Exhibit 1F

**2020-08-03** - Tri-County Orthopedic Associates - Dr. Marcus Greene
- Orthopedic consultation for persistent lumbar radiculopathy
- Subjective: NSAIDs provide some relief but functional activities limited, unable to return to warehouse job
- Objective: Antalgic gait, lumbar flexion 50%, extension 30%, positive straight leg raise left at 35°, weakness left L5 dorsiflexion 4/5, sensory deficit left L5 dermatome
- Imaging: MRI showed left paracentral disc protrusion at L4-L5 causing moderate stenosis impinging L5 nerve root
- Assessment: L4-L5 disc herniation with left L5 radiculopathy
- Plan: Series of epidural steroid injections, 6-week PT 3x/week, continue current medications
- Source: Exhibit 2F

**2020-09-15** - Riverside Pain Management Center - Dr. Helen Cho
- First epidural steroid injection
- Subjective: Pain 7/10
- Procedure: Left L4-L5 transforaminal epidural steroid injection under fluoroscopy, Dexamethasone and Lidocaine injected
- Assessment: L4-L5 disc herniation with radiculopathy
- Source: Exhibit 3F

**2020-10-01** - Riverside Pain Management Center - Dr. Helen Cho
- Second epidural steroid injection
- Subjective: First procedure provided ~40% pain relief for ~10 days, current pain 5/10
- Procedure: Second left L4-L5 transforaminal ESI with Betamethasone and Bupivacaine
- Source: Exhibit 3F

**2020-11-10** - Lakewood Family Medicine - Dr. Anita Patel
- Follow-up after epidural injections
- Subjective: Moderate improvement, pain 4/10 at rest, 6/10 with exertion, completed 12 PT sessions, unable to resume full work duties
- Objective: BP 128/80, better lumbar ROM, negative straight leg raise bilaterally, normal gait, diminished tenderness
- Labs: Ordered
- Assessment: Improving lumbar radiculopathy, new pre-diabetes
- Plan: Metformin 500mg daily, Naproxen PRN, work restrictions lifting <20 lbs, sitting <30 min consecutively, nutrition consult
- Source: Exhibit 1F

**2021-03-22** - Tri-County Orthopedic Associates - Dr. Marcus Greene
- Orthopedic follow-up ~5 months post-injection series
- Subjective: Pain plateau at 4-5/10, intermittent left leg numbness, employer terminated position due to physical limitations
- Objective: Lumbar flexion improved to 60%, negative straight leg raise, motor strength 5/5 bilaterally, mild sensory decrease left L5 dermatome persists
- Imaging: New MRI showed stable L4-L5 disc protrusion, newly noted mild facet arthropathy
- Assessment: Reached MMI from surgical standpoint, recommend continued conservative care
- Plan: Permanent work restrictions no lifting >15 lbs, no repetitive bending/twisting, trial Gabapentin for neuropathic symptoms
- Source: Exhibit 2F

**2021-07-14** - Lakewood Family Medicine - Dr. Anita Patel
- Annual physical
- Subjective: Back pain stable 3-4/10 with gabapentin, occasional left leg numbness, feeling depressed since job loss, trouble sleeping
- Objective: Wt 205 lbs, BP 138/88, PHQ-9 score 14 (moderate depression), lumbar exam unchanged
- Labs: HbA1c 6.1% (pre-diabetic), Total cholesterol 232, LDL 148, HDL 42, Triglycerides 210, Vitamin D 18 ng/mL (low), TSH 2.4 (normal)
- Assessment: Pre-diabetes, Hyperlipidemia, Major depressive disorder moderate, Vitamin D deficiency, Chronic lumbar radiculopathy
- Plan: Continue current medications, recheck HbA1c and lipids in 3 months, mental health follow-up in 4 weeks, consider psychiatry referral
- Medications: Metformin 1000mg daily, Atorvastatin 20mg daily, Sertraline 50mg daily, Vitamin D3 5000 IU daily, Gabapentin 300mg TID
- Referrals: Nutritionist, psychiatry if needed
- Source: Exhibit 1F / Addendum

**2021-11-02** - Bayview Behavioral Health - Dr. Sandra Kim
- Initial psychiatric evaluation
- Subjective: Referred by PCP, mood decline despite sertraline 50mg x 4 months, insomnia, anhedonia, poor motivation, anxiety about finances and disability claim, denies SI/HI
- Objective: Cooperative, speech low volume, mood "down and worried", constricted affect, linear/goal-directed thought process, intact cognition
- Assessment: Major depressive disorder moderate recurrent, Generalized anxiety disorder, Adjustment disorder with mixed anxiety and depressed mood
- Plan: Increase sertraline to 100mg daily, Hydroxyzine 25mg PRN for anxiety, weekly individual therapy
- Source: Exhibit 4F / Addendum

**2022-02-17** - Lakewood Family Medicine - Dr. Anita Patel
- Management of metabolic and mental health conditions
- Subjective: Mood better since sertraline increase and therapy, sleep improved, back pain stable, gained 10 lbs
- Objective: Wt 215 lbs (BMI 30.1), BP 140/90
- Labs: HbA1c 6.4% (HIGH), Fasting glucose 128 mg/dL (HIGH)
- Assessment: Type 2 diabetes mellitus, Stage 1 hypertension, obesity
- Plan: Lisinopril 10mg daily, Metformin increased to 1000mg BID, Atorvastatin increased to 40mg daily
- Source: Exhibit 1F

**2022-06-08** - Heartland Cardiology Group - Dr. James Whitfield
- Cardiology consultation for newly diagnosed hypertension
- Subjective: Occasional chest tightness during exertion that abates with rest
- Objective: BP 142/88, cardiac exam unremarkable
- Testing: Echo EF 60% with mild LVH, exercise stress test negative for ischemia after 8.5 minutes
- Assessment: Essential hypertension with mild LVH, metabolic syndrome
- Plan: Continue Lisinopril, consider adding Amlodipine if BP remains elevated
- Source: Exhibit 5F

**2022-10-25** - Riverside Pain Management Center - Dr. Helen Cho
- Pain management follow-up
- Subjective: Worsening back pain past 3 months, pain 6/10 with radiation to buttock and posterior thigh, Gabapentin somewhat helpful but causes sedation
- Objective: Lumbar flexion 50%, extension 25%, positive straight leg raise left at 50°
- Imaging: Lumbar X-ray showed L4-L5 disc space narrowing, Grade I degenerative spondylolisthesis at L4-L5
- Plan: Switch to Pregabalin, series of diagnostic lumbar medial branch blocks to evaluate for radiofrequency ablation
- Source: Exhibit 3F

**2023-01-18** - Riverside Pain Management Center - Dr. Helen Cho
- Bilateral medial branch block procedure
- Subjective: Presents for L4-L5 and L5-S1 bilateral medial branch block, reports pregabalin providing moderate relief
- Procedure: Bilateral L4, L5, S1 medial branch blocks under fluoroscopic guidance, Bupivacaine 0.5% 0.5mL at each level
- Plan: If >80% pain relief for 6+ hours, proceed with radiofrequency ablation, pain diary for 48 hours, return in 2 weeks
- Source: Exhibit 3F / Addendum

**2023-04-05** - Riverside Pain Management Center - Dr. Helen Cho
- Radiofrequency ablation
- Subjective: Both temporary blocks provided >80% relief for several hours
- Procedure: Bilateral L4, L5, S1 medial branch radiofrequency ablation, lesioning at 80°C for 90 seconds at each targeted nerve after sensory/motor testing
- Source: Exhibit 3F

**2023-08-22** - Lakewood Family Medicine - Dr. Anita Patel
- Follow-up
- Subjective: Significant improvement in back pain following radiofrequency ablation, pain 2-3/10, mood stable
- Objective: BP 126/78, Wt 212 lbs, PHQ-9 score 6
- Assessment: Well-controlled Type 2 diabetes, controlled hypertension, depression in partial remission
- Plan: Continue all current medications including Amlodipine 5mg added by cardiology, completed SSA disability paperwork
- Source: Exhibit 1F

**2024-01-10** - Independent Medical Examination Office - Dr. Robert Hargrove
- Independent consultative examination for disability determination
- Subjective: Chronic low back pain with radiation into left leg, depression and anxiety, pain limits sitting/standing/walking
- Objective: Ht 5'10", Wt 214 lbs (BMI 30.7), BP 130/82, lumbar flexion 55°, extension 35°, negative straight leg raise bilaterally, motor strength 5/5 all muscle groups, sensation decreased subjectively in left L5 but intact with monofilament, grip strength 85 lbs left, 90 lbs right
- Testing: PHQ-9 = 8, GAD-7 = 6
- Assessment: Chronic lumbar disc disease with residual left L5 radiculopathy, Type 2 diabetes, essential hypertension, Major depressive disorder in partial remission
- Source: Exhibit 10F

Now I'll organize these chronologically and format them properly. The dates span from 2020-06-12 through 2024-01-10, with multiple visits across different specialties including primary care, orthopedics, pain management, behavioral health, cardiology, and independent medical examination.

I need to be careful about the formatting requirements - each date gets an H2 heading, then an H3 subheading with the same date, followed by bullet points for the details. I should also note that imaging and lab results are documented separately in exhibits 8F and 9F, so I'll reference those appropriately rather than repeating all the findings here.
</think>

## Date of Medical Visit: 06/12/2020
### 06/12/2020
* **Type of Visit:** Primary Care - Initial Evaluation
* **Facility Name:** Lakewood Family Medicine
* **Provider Name:** Anita Patel, MD
* **Subjective/HPI/CC/Hospital Course:** Patient presents with a three-month history of persistent low back pain which travels down his left leg, a condition he associates with a lifting incident at his former job. Pain was noted to be 6 out of 10 and was exacerbated by extended periods of sitting.
* **Objective/PE:** Blood pressure 132/84, heart rate 78, weight 198 pounds. Notable limitation in the range of motion of lumbar spine. Positive straight leg raise test on the left side at 40-degree angle. Tenderness in the L4-L5 paraspinal area. Deep tendon reflexes assessed as 2+/2+ at the patella and 1+/2+ at the Achilles.
* **Diagnoses:** Lumbar radiculopathy, lumbar disc degeneration.
* **Plan/Assessment:** Prescribed Naproxen 500mg to be taken twice daily and Cyclobenzaprine 10mg at bedtime. Referral made to orthopedic spine specialist.
* **Source References:** Exhibit 1F (Page 1 of 6)

## Date of Medical Visit: 08/03/2020
### 08/03/2020
* **Type of Visit:** Orthopedic Consultation
* **Facility Name:** Tri-County Orthopedic Associates
* **Provider Name:** Marcus Greene, DO
* **Subjective/HPI/CC/Hospital Course:** Patient reports that NSAIDs offer some relief but functional activities are still limited, preventing return to warehouse job.
* **Objective/PE:** Antalgic gait. Lumbar flexion restricted to 50 percent and extension to 30 percent. Positive straight leg raise test on the left at 35 degrees. Weakness in left-sided L5 dorsiflexion, graded at 4/5 strength, compared to 5/5 on the right. Sensory deficit noted in left L5 dermatome.
* **Imaging:** MRI of lumbar spine demonstrated left paracentral disc protrusion at L4-L5 causing moderate stenosis and impinging on the L5 nerve root.
* **Diagnoses:** L4-L5 disc herniation with associated left L5 radiculopathy.
* **Plan/Assessment:** Plan involved a series of epidural steroid injections and a six-week course of physical therapy, three times per week. Continue current medications.
* **Source References:** Exhibit 2F (Page 2 of 6)

## Date of Medical Visit: 09/15/2020
### 09/15/2020
* **Type of Visit:** Pain Management - Procedure (Epidural Steroid Injection)
* **Facility Name:** Riverside Pain Management Center
* **Provider Name:** Helen Cho, MD
* **Subjective/HPI/CC/Hospital Course:** Patient presents for first of planned series of three epidural steroid injections at L4-L5 level. Pain rated at 7/10.
* **Surgery/Procedure:** Left L4-L5 transforaminal epidural steroid injection performed under fluoroscopic guidance. Contrast used to confirm appropriate spread. Combination of Dexamethasone and Lidocaine injected.
* **Diagnoses:** L4-L5 disc herniation with radiculopathy.
* **Source References:** Exhibit 3F (Page 2 of 6)

## Date of Medical Visit: 10/01/2020
### 10/01/2020
* **Type of Visit:** Pain Management - Procedure (Epidural Steroid Injection)
* **Facility Name:** Riverside Pain Management Center
* **Provider Name:** Helen Cho, MD
* **Subjective/HPI/CC/Hospital Course:** Patient reports first procedure provided about 40% pain relief which lasted for roughly 10 days. Pain currently 5/10.
* **Surgery/Procedure:** Second left L4-L5 transforaminal epidural steroid injection performed using Betamethasone and Bupivacaine.
* **Source References:** Exhibit 3F (Page 2 of 6)

## Date of Medical Visit: 11/10/2020
### 11/10/2020
* **Type of Visit:** Primary Care - Follow-up
* **Facility Name:** Lakewood Family Medicine
* **Provider Name:** Anita Patel, MD
* **Subjective/HPI/CC/Hospital Course:** Patient conveys moderate level of improvement, with pain level at rest down to 4/10, though it escalates to 6/10 with physical exertion. Finished course of 12 physical therapy sessions but remains unable to resume full work duties.
* **Objective/PE:** Blood pressure 128/80. Lumbar spine exam shows better range of motion. Straight leg raise test now negative on both sides. Gait appears normal. Tenderness diminished.
* **Labs:** Laboratory studies ordered.
* **Diagnoses:** Improving lumbar radiculopathy, new finding of pre-diabetes.
* **Plan/Assessment:** Medication regimen adjusted to include Metformin 500mg daily, with Naproxen to be used as needed. Work restrictions issued, limiting lifting to under 20 pounds and sitting to no more than 30 minutes consecutively. Nutrition consult recommended.
* **Source References:** Exhibit 1F (Page 1 of 6)

## Date of Medical Visit: 03/22/2021
### 03/22/2021
* **Type of Visit:** Orthopedic Follow-up
* **Facility Name:** Tri-County Orthopedic Associates
* **Provider Name:** Marcus Greene, DO
* **Subjective/HPI/CC/Hospital Course:** Patient reports pain has reached a plateau at 4-5/10 level and continues to experience intermittent numbness in left leg. Informs Dr. Greene that employer terminated his position due to physical limitations.
* **Objective/PE:** Lumbar flexion improved to 60 percent. Straight leg raise test negative. Motor strength now 5/5 bilaterally. Mild sensory decrease persists in left L5 dermatome.
* **Imaging:** New MRI showed stable L4-L5 disc protrusion and newly noted mild facet arthropathy.
* **Diagnoses:** L4-L5 disc herniation with left L5 radiculopathy.
* **Plan/Assessment:** Patient had reached maximum medical improvement from a surgical standpoint. Recommended continued conservative care. Issued permanent work restrictions of no lifting over 15 pounds and no repetitive bending or twisting. Trial of Gabapentin started for neuropathic symptoms.
* **Source References:** Exhibit 2F (Page 2 of 6)

## Date of Medical Visit: 07/14/2021
### 07/14/2021
* **Type of Visit:** Primary Care - Annual Physical
* **Facility Name:** Lakewood Family Medicine
* **Provider Name:** Anita Patel, MD
* **Subjective/HPI/CC/Hospital Course:** Patient describes back pain as stable at 3-4/10 level, managed with gabapentin, and notes occasional numbness in left leg. Reports feeling depressed and having trouble sleeping since employment was terminated.
* **Objective/PE:** Weight increased to 205 pounds. Blood pressure measured at 138/88. PHQ-9 screening yielded score of 14, indicating moderate depression. Back exam findings unchanged.
* **Labs:** HbA1c 6.1% (pre-diabetic). Lipid panel: Total cholesterol 232, LDL 148, HDL 42, Triglycerides 210. TSH 2.4 (normal). Vitamin D 18 ng/mL (low).
* **Diagnoses:** Pre-diabetes, hyperlipidemia, moderate major depressive disorder, Vitamin D deficiency, chronic lumbar radiculopathy.
* **Plan/Assessment:** Medications adjusted to Metformin 1000mg daily, Atorvastatin 20mg daily, and new prescription for Sertraline 50mg daily initiated. Advised to take Vitamin D3 5000 IU. Recheck HbA1c and lipids in 3 months. Mental health follow-up in 4 weeks. Consider psychiatry referral if no improvement with sertraline.
* **Referrals:** Nutritionist for diet counseling; psychiatry if needed.
* **Source References:** Exhibit 1F (Page 1 of 6), Addendum (Page 6 of 6)

## Date of Medical Visit: 11/02/2021
### 11/02/2021
* **Type of Visit:** Psychiatric Evaluation
* **Facility Name:** Bayview Behavioral Health
* **Provider Name:** Sandra Kim, PsyD
* **Subjective/HPI/CC/Hospital Course:** Patient referred by PCP for evaluation of depression and anxiety. Reports decline in mood despite taking 50mg of sertraline for four months. Endorses insomnia, anhedonia, and poor motivation. Anxiety centered on financial situation and disability claim. Denies suicidal or homicidal ideation.
* **Objective/PE:** Cooperative man with speech of low volume and constricted affect. Mood described as "down and worried." Thought process linear and goal-directed. Cognition intact.
* **Diagnoses:** Major Depressive Disorder, recurrent and moderate; Generalized Anxiety Disorder; Adjustment Disorder with mixed anxiety and depressed mood related to chronic pain and unemployment.
* **Plan/Assessment:** Increase sertraline to 100mg daily. Prescribe Hydroxyzine as needed for anxiety. Begin weekly individual therapy. Supportive counseling for disability process.
* **Source References:** Exhibit 4F (Page 2 of 6), Addendum (Page 6 of 6)

## Date of Medical Visit: 02/17/2022
### 02/17/2022
* **Type of Visit:** Primary Care - Management Visit
* **Facility Name:** Lakewood Family Medicine
* **Provider Name:** Anita Patel, MD
* **Subjective/HPI/CC/Hospital Course:** Patient states mood has gotten better since sertraline dose was increased and he started therapy. Sleep has also improved. Back pain stable. However, he has gained an additional 10 pounds.
* **Objective/PE:** Weight now at 215 lbs (BMI 30.1). Blood pressure elevated at 140/90.
* **Labs:** HbA1c 6.4% (HIGH), Fasting glucose 128 mg/dL (HIGH).
* **Diagnoses:** Type 2 diabetes mellitus, Stage 1 hypertension, obesity.
* **Plan/Assessment:** New prescription for Lisinopril 10mg daily provided. Metformin increased to 1000mg twice daily. Atorvastatin increased to 40mg daily.
* **Source References:** Exhibit 1F (Page 1 of 6)

## Date of Medical Visit: 06/08/2022
### 06/08/2022
* **Type of Visit:** Cardiology Consultation
* **Facility Name:** Heartland Cardiology Group
* **Provider Name:** James Whitfield, MD
* **Subjective/HPI/CC/Hospital Course:** Cardiology consultation for evaluation of newly diagnosed hypertension. Patient mentions occasional chest tightness during exertion that abates with rest.
* **Objective/PE:** Blood pressure in clinic 142/88. Cardiac exam unremarkable.
* **Imaging:** Echocardiogram revealed normal ejection fraction of 60% with mild left ventricular hypertrophy. Exercise stress test negative for ischemia after 8.5 minutes.
* **Diagnoses:** Essential hypertension with mild LVH, metabolic syndrome.
* **Plan/Assessment:** Plan to continue lisinopril and consider adding amlodipine if blood pressure remains elevated.
* **Source References:** Exhibit 5F (Page 2 of 6)

## Date of Medical Visit: 10/25/2022
### 10/25/2022
* **Type of Visit:** Pain Management Follow-up
* **Facility Name:** Riverside Pain Management Center
* **Provider Name:** Helen Cho, MD
* **Subjective/HPI/CC/Hospital Course:** Visit prompted by worsening of back pain over prior three months. Patient rates pain at 6/10 with radiation into buttock and posterior thigh. Notes Gabapentin only somewhat helpful and causes sedation.
* **Objective/PE:** Examination shows lumbar flexion at 50% and extension at 25%. Straight leg raise positive on left at 50 degrees.
* **Imaging:** Recent lumbar X-ray showed L4-L5 disc space narrowing and Grade I degenerative spondylolisthesis at L4-L5.
* **Plan/Assessment:** Plan to switch medication to Pregabalin and perform series of diagnostic lumbar medial branch blocks to see if patient is candidate for radiofrequency ablation.
* **Source References:** Exhibit 3F (Page 2 of 6)

## Date of Medical Visit: 01/18/2023
### 01/18/2023
* **Type of Visit:** Pain Management - Procedure (Medial Branch Block)
* **Facility Name:** Riverside Pain Management Center
* **Provider Name:** Helen Cho, MD
* **Subjective/HPI/CC/Hospital Course:** Patient presents for L4-L5 and L5-S1 bilateral medial branch block. Reports pregabalin providing moderate relief.
* **Surgery/Procedure:** Bilateral medial branch block procedure at L4, L5, and S1 levels with Bupivacaine 0.5% 0.5mL at each level performed under fluoroscopic guidance.
* **Plan/Assessment:** If greater than 80% pain relief for 6 or more hours, proceed with radiofrequency ablation. Pain diary for 48 hours. Return in 2 weeks for evaluation and possible second diagnostic block.
* **Source References:** Exhibit 3F (Page 2 of 6), Addendum (Page 6 of 6)

## Date of Medical Visit: 04/05/2023
### 04/05/2023
* **Type of Visit:** Pain Management - Procedure (Radiofrequency Ablation)
* **Facility Name:** Riverside Pain Management Center
* **Provider Name:** Helen Cho, MD
* **Subjective/HPI/CC/Hospital Course:** Patient reports that both temporary blocks had given him more than 80% relief for several hours.
* **Surgery/Procedure:** Bilateral L4, L5, and S1 medial branch radiofrequency ablation performed. Procedure involved lesioning at 80 degrees Celsius for 90 seconds at each targeted nerve after appropriate sensory and motor testing.
* **Source References:** Exhibit 3F (Page 2 of 6)

## Date of Medical Visit: 08/22/2023
### 08/22/2023
* **Type of Visit:** Primary Care Follow-up
* **Facility Name:** Lakewood Family Medicine
* **Provider Name:** Anita Patel, MD
* **Subjective/HPI/CC/Hospital Course:** Patient reports significant improvement in back pain following radiofrequency ablation procedure, with pain levels now at 2-3/10. Mood stable.
* **Objective/PE:** Blood pressure well-controlled at 126/78. Weight 212 pounds. PHQ-9 score decreased to 6.
* **Diagnoses:** Well-controlled Type 2 diabetes, controlled hypertension, depression in partial remission.
* **Plan/Assessment:** All current medications continued, including Amlodipine 5mg which had been added by cardiology. Dr. Patel completed disability paperwork for the Social Security Administration during this visit.
* **Source References:** Exhibit 1F (Page 1 of 6)

## Date of Medical Visit: 01/10/2024
### 01/10/2024
* **Type of Visit:** Independent Medical Examination (Consultative)
* **Facility Name:** Independent Medical Examination Office
* **Provider Name:** Robert Hargrove, MD
* **Subjective/HPI/CC/Hospital Course:** Patient presents with chief complaint of chronic low back pain with radiation into left leg, as well as depression and anxiety. Reports pain limits ability to sit, stand, and walk for prolonged periods.
* **Objective/PE:** Patient is 5'10" and weighs 214 pounds (BMI 30.7). Blood pressure 130/82. Examination of lumbar spine revealed flexion to 55 degrees and extension to 35 degrees. Straight leg raising negative bilaterally. Motor strength graded 5/5 in all muscle groups in both upper and lower extremities. Sensation subjectively described as decreased in left L5 distribution but found intact when tested with monofilament. Grip strength strong at 85 pounds on left and 90 pounds on right.
* **Social:** Patient reports difficulty with concentration and memory.
* **Diagnoses:** Chronic lumbar disc disease with residual left L5 radiculopathy, Type 2 diabetes, essential hypertension, major depressive disorder in partial remission.
* **Plan/Assessment:** PHQ-9 scored 8; GAD-7 scored 6.
* **Source References:** Exhibit 10F (Page 3 of 6)