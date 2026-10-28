"""Build index.html / critical-four.embed.html from game.html + the case list below.

Every case belongs to one opponent (domonic, matilda, hannah, myvi, lightbox) and has
one or more image SERIES. A series is either a single image (an X-ray view) or a
folder of slices (a scrollable CT/MRI stack):

    {"label": "PA",          "file": "dom1/pa.png"}       one image
    {"label": "Axial brain", "dir":  "mat1/axial"}        every image in that folder,
                                                          in natural filename order
                                                          (slice_2 before slice_10)
    {"label": "Axial", "dir": "mat1/axial", "reverse": True}   flip the order if the
                                                          export runs feet-to-head

Paths are relative to assets/src/. The build converts everything to greyscale JPEG
in assets/cases/<id>/ and, for the full build, inlines it so the output is one
self-contained file.

A case with "placeholder": True needs no images: the game draws a labelled stand-in
film (or a fake scrollable stack for CT/MRI) so the whole flow can be played before
the real studies arrive.

Usage:  python build.py            -> index.html + critical-four.embed.html (self-contained)
        python build.py --preview  -> _preview.html (references assets/cases/ files; for local testing)
"""
import base64, json, re, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).parent
A = ROOT / "assets"
XRAY_SIDE, STACK_SIDE = 1400, 768
OPPONENTS = ["domonic", "matilda", "hannah", "myvi", "lightbox"]


def ph(cid, opp, modality, label):
    """A placeholder case: same shape as a real one, so swapping in real content is a straight edit."""
    return {
        "id": cid, "opponent": opp, "modality": modality, "label": label, "placeholder": True,
        "history": "Clinical history to be added.",
        "question": "What is the urgent finding?",
        "options": ["Answer A (correct, placeholder)", "Answer B", "Answer C", "Answer D"],
        "answer": 0,
        "finding": "Finding to be added.",
        "clue": "Key imaging clue to be added.",
        "why": "Why it matters to be added.",
        "series": [], "source": None,
    }


# ---------------------------------------------------------------------------------
# THE 30 CASES. Each opponent has exactly six.
#   modality  "X-ray", "CT" or "MRI" (CT/MRI with a multi-slice series count as
#             scrollable, which matters for the "Scroll Model" marker)
#   label     shown above the study, e.g. "Chest X-ray, PA"
#   history   one-line clinical context shown with the question
#   options   exactly four; "answer" is the index of the correct one (0-3).
#             The game shuffles the order on screen.
#   finding / clue / why   the three-part explanation shown once the case is solved
#   series    list of series in viewing order (see top of file)
#   source    key into SOURCES for the image credit (or a list of keys), or None
#   overlay   optional, on a single-image series: a white-on-black mask (same framing as
#             the image) shown as a tinted overlay the player can switch on and off
#   overlay_dir  the same for a stack: a folder with one mask per slice
#   start     optional: slice to open a stack on (0 = first)
#   reveal    optional: {"series": [...], "lines": [...]} shown after a correct answer,
#             with the examiner talking the player through it (e.g. the AP that shows
#             the fracture behind a soft-tissue sign)
# ---------------------------------------------------------------------------------
CASES = [
    # Domonic: chest pathology and chest lines/tubes
    {
        "id": "dom1", "opponent": "domonic", "modality": "X-ray", "label": "Chest X-ray, PA",
        "history": "Young adult with sudden right-sided chest pain and shortness of breath.",
        "question": "What is the urgent finding?",
        "options": ["Right pneumothorax", "Left pneumothorax", "Skin fold", "Normal chest X-ray"],
        "answer": 0,
        "finding": "Right pneumothorax: air between the lung and the chest wall, from the apex down the lateral chest.",
        "clue": "A thin white line (the visceral pleura) runs parallel to the chest wall, with no lung markings beyond it. A skin fold usually runs past the edge of the chest and has lung markings on both sides.",
        "why": "A pneumothorax can enlarge, and a tension pneumothorax compromises breathing and circulation. The mediastinum here is central, so there is no sign of tension, but the finding still needs escalating straight away.",
        "series": [{"label": "PA", "file": "dom1/xray.jpg"}],
        "reveal": {
            "series": [{"label": "PA, marked", "file": "dom1/xray.jpg", "overlay": "dom1/mask.jpg"}],
            "lines": [
                "This is where it was hiding. I've shaded the air outside the right lung.",
                "Trace the thin white pleural line from the apex down the side of the chest. Beyond it, there are no lung markings at all.",
                "Switch the overlay off with the OVERLAY button and find the edge yourself.",
                "The trachea and heart haven't shifted, so there's no tension. It still gets escalated straight away. Nothing slips past me.",
            ],
        },
        "source": "ptx498",
    },
    {
        "id": "dom2", "opponent": "domonic", "modality": "X-ray", "label": "Chest X-ray (left side shown)",
        "history": "Young adult with sudden chest pain and a feeling of crackling under the skin of the neck after a bout of severe coughing.",
        "question": "The red arrows are your hint. What is the finding?",
        "options": ["Pneumomediastinum", "Left pneumothorax", "Pneumopericardium", "Skin fold"],
        "answer": 0,
        "finding": "Pneumomediastinum: free air in the mediastinum. On the X-ray it shows as a thin lucent line running parallel to the left heart and mediastinal border (arrows). The coronal CT confirms air around the mediastinal structures, tracking up into the neck as soft-tissue emphysema, and also shows a small right interlobar pneumothorax.",
        "clue": "Look for a thin white line (the mediastinal pleura) with dark air beside it, hugging the heart and mediastinal borders rather than the chest wall, and for air streaking up into the neck. A pneumopericardium stays around the heart and doesn't track above it.",
        "why": "It is often benign, for example after severe coughing or asthma, but it can be the first sign of a ruptured oesophagus or a torn airway, which are emergencies. It needs escalating so the cause is found.",
        "series": [{"label": "Chest X-ray", "file": "dom2/xray_arrows.jpg"}],
        "reveal": {
            "series": [{"label": "CT, coronal (lung window)", "file": "dom2/ct_coronal.jpg"}],
            "lines": [
                "Here's the CT. See the black air tracking around the middle of the chest, outlining the mediastinal structures?",
                "Follow it up: the air spreads into the neck as soft-tissue emphysema. On the X-ray it made that thin line beside the heart border.",
                "Pneumopericardium hugs the heart only; this climbs past it into the neck. Bonus spot: a small right interlobar pneumothorax.",
                "Usually it's benign, but it can mean a torn airway or a ruptured oesophagus. Nothing slips past me, so escalate it.",
            ],
        },
        "downloads": [
            {"label": "original image (Wikimedia Commons)", "url": "https://upload.wikimedia.org/wikipedia/commons/7/76/Mediastinalemphysem_-_Roe_vs_CT_LF.jpg"},
            {"label": "adapted X-ray panel (JPEG)", "file": "dom2/xray_arrows.jpg", "name": "Pneumomediastinum_X-ray-panel_adapted-from-Hellerhoff_CC-BY-SA-3.0.jpg"},
            {"label": "adapted CT panel (JPEG)", "file": "dom2/ct_coronal.jpg", "name": "Pneumomediastinum_CT-panel_adapted-from-Hellerhoff_CC-BY-SA-3.0.jpg"},
        ],
        "source": "hellerhoff_pmed",
    },
    {
        "id": "dom3", "opponent": "domonic", "modality": "X-ray", "label": "Chest X-ray, AP (ward film after intubation)",
        "history": "Ventilated adult on the intensive care unit whose oxygen levels have dropped since being moved.",
        "question": "What is the urgent finding?",
        "options": ["Endotracheal tube in the right main bronchus", "Endotracheal tube correctly placed", "Endotracheal tube in the oesophagus", "Right pneumothorax"],
        "answer": 0,
        "finding": "The endotracheal tube tip lies in the right main bronchus, below the carina. The left lung is poorly aerated, with opacity at the left base.",
        "clue": "Find the carina, where the trachea splits in two. The tube tip should sit about 3-5 cm above it. The right main bronchus is wider and straighter than the left, so a tube pushed too far usually goes right.",
        "why": "Only one lung is being ventilated. The other collapses and oxygen levels fall, and the ventilated lung can be over-inflated. The tube needs pulling back and its position rechecking, so tell the team straight away.",
        "series": [{"label": "AP", "file": "dom3/ett_clean.jpg"}],
        "reveal": {
            "series": [{"label": "AP, arrowed", "file": "dom3/ett_annotated.jpg"}],
            "lines": [
                "Follow the tube down. See my arrow? The tip has slipped past the carina into the right main bronchus.",
                "The right bronchus is wider and straighter, so that's where an over-eager tube ends up.",
                "Now the left lung: it's barely getting any air and it's collapsing at the base.",
                "Tip 3 to 5 cm above the carina. Tell the team now so they can pull it back. Nothing slips past me, not even a tube.",
            ],
        },
        "downloads": [
            {"label": "original image (Wikimedia Commons)", "url": "https://upload.wikimedia.org/wikipedia/commons/7/76/Tubusspitze_im_rechten_Hauptbronchus_64W_-_CR_ap_-_001.jpg"},
            {"label": "original annotated image (Wikimedia Commons)", "url": "https://upload.wikimedia.org/wikipedia/commons/c/c6/Tubusspitze_im_rechten_Hauptbronchus_64W_-_CR_ap_-_001_-_Annotation.jpg"},
        ],
        "source": ["hellerhoff_ett", "hellerhoff_ett_ann"],
    },
    {
        "id": "dom4", "opponent": "domonic", "modality": "X-ray", "label": "Chest X-ray, AP portable, upright (child)",
        "history": "Child brought in after a road traffic collision, struggling to breathe, with a falling blood pressure.",
        "question": "What is the urgent finding?",
        "options": ["Right tension pneumothorax", "Left tension pneumothorax", "Large left pleural effusion", "Right lower lobe collapse"],
        "answer": 0,
        "finding": "Right tension pneumothorax: the right lung has collapsed towards the hilum, the right side of the chest is dark with no lung markings, and the heart and mediastinum are pushed across to the left.",
        "clue": "Look beyond the black lung: a tension pneumothorax pushes things. The mediastinum and trachea shift away from the dark side, and the diaphragm may be flattened. The white left side here is the left lung and mediastinum squashed across, not a pleural effusion.",
        "why": "Tension pneumothorax is an emergency that can stop the heart. It should be treated with immediate needle or finger decompression, ideally before any X-ray is taken. If you see these signs on an image, tell the team instantly.",
        "series": [{"label": "AP", "file": "dom4/tension_clean.png"}],
        "reveal": {
            "series": [{"label": "AP, annotated", "file": "dom4/tension_annotated.png"}],
            "lines": [
                "Look at the right side: black, no lung markings, and the lung squashed down towards the hilum. The red line marks its edge.",
                "Now the part that makes it tension: the heart and mediastinum are shoved across to the left. That's what the blue arrows show.",
                "That white left side isn't an effusion. It's the left lung and heart squashed by the pressure.",
                "This one can't wait for a report. Decompress it now. Nothing slips past me, and this can't slip past you.",
            ],
        },
        "downloads": [
            {"label": "original article (eScholarship)", "url": "https://escholarship.org/uc/item/5f444352"},
            {"label": "adapted image, annotations removed (PNG)", "file": "dom4/tension_clean.png", "name": "Tension-pneumothorax_annotations-removed_adapted-from-Tritsch-Galan-Oates_CC-BY-4.0.png"},
        ],
        "source": "tritsch_tension",
    },
    {
        "id": "dom5", "opponent": "domonic", "modality": "X-ray", "label": "Chest and upper abdomen X-ray, AP (child)",
        "history": "Toddler brought in after a parent found an open pack of button batteries. Currently well.",
        "question": "What is the finding?",
        "options": ["Ingested button battery", "Ingested coin", "ECG electrode on the skin", "Normal study"],
        "answer": 0,
        "finding": "An ingested button battery, a dense smooth-edged disc projected over the upper abdomen just below the left hemidiaphragm, in the stomach (as described by the image source).",
        "clue": "Batteries and coins look alike. Seen face-on, a button battery shows a double-ring (halo) edge; seen side-on it has a stepped rim. A coin has neither. Then pin down where it is: oesophagus, stomach or beyond.",
        "why": "Button batteries can burn through tissue within hours. One in the oesophagus is an emergency needing removal straight away. Even past the chest, young children and larger batteries may still need urgent endoscopy, so image the whole route from neck to abdomen and escalate the result immediately.",
        "series": [{"label": "AP", "file": "dom3/no_arrow.png"}],
        "reveal": {
            "series": [{"label": "AP, arrowed", "file": "dom3/original_arrow.png"}],
            "lines": [
                "There, just under the diaphragm on the left: a dense, smooth-edged disc. That's a button battery, sitting in the stomach.",
                "Coins and batteries look alike. Look for the double-ring halo face-on, or a stepped rim side-on. A coin has neither.",
                "It's below the chest, but only just. Always image the whole route, neck to abdomen, so you know exactly where it is.",
                "In the oesophagus a battery can burn through within hours, and little ones may need it out even from the stomach. Escalate it now.",
            ],
        },
        "downloads": [
            {"label": "original image (Wikimedia Commons)", "url": "https://upload.wikimedia.org/wikipedia/commons/3/3a/ButtonBatteryIngestion.png"},
            {"label": "adapted image, arrow removed (PNG)", "file": "dom3/no_arrow.png", "name": "Button-battery_arrow-removed_adapted-from-Doc-James_CC-BY-SA-4.0.png"},
        ],
        "source": "docjames_battery",
    },
    {
        "id": "dom6", "opponent": "domonic", "modality": "X-ray", "label": "Neck X-ray, AP and lateral (child)",
        "history": "Young child seen swallowing something at home, now drooling and refusing to eat.",
        "question": "The AP shows a halo and the lateral a step-off. What was removed from this child's oesophagus?",
        "options": ["Two coins stuck together (a coin stack)", "A button battery", "A single coin", "A magnet"],
        "answer": 0,
        "finding": "A coin stack in the upper oesophagus: a quarter and a nickel stuck together with saliva. It mimicked a button battery, with a halo sign on the AP view and a step-off on the lateral.",
        "clue": "A coin stack and a button battery can both show a halo (double ring) and a step-off. Here the steps on the lateral are uneven, which fits two coins of different sizes, but plain films cannot reliably tell the two apart.",
        "why": "A button battery can burn through the oesophagus within hours, so anything that looks like one is treated as one and removed urgently. That was the right call here, even though it turned out to be coins.",
        "series": [{"label": "AP", "file": "dom4/ap_halo.jpg"}, {"label": "Lateral", "file": "dom4/lateral_stepoff.jpg"}],
        "reveal": {
            "series": [{"label": "AP", "file": "dom4/ap_halo.jpg"}, {"label": "Lateral", "file": "dom4/lateral_stepoff.jpg"}],
            "lines": [
                "Gotcha. Halo on the AP, step-off on the lateral: everyone shouted 'button battery', and fair enough.",
                "But look at the steps on the lateral. They're uneven. That's two coins of different sizes stuck together.",
                "In theatre: a quarter and a nickel, glued together by spit. A coin stack in disguise.",
                "Lesson: if it might be a battery, treat it like one. Better a rushed coin than a burnt oesophagus.",
            ],
        },
        "source": "ware_coinstack",
    },
    # Matilda: neurological emergencies
    {
        "id": "mat1", "opponent": "matilda", "modality": "MRI", "label": "MRI brain, DWI and FLAIR",
        "history": "Adult with sudden right arm weakness and difficulty getting words out.",
        "question": "What is the urgent finding?",
        "options": ["Acute left MCA territory infarct", "Acute right MCA territory infarct", "Intracerebral haemorrhage", "No acute abnormality"],
        "answer": 0,
        "finding": "Acute infarct in the left frontal lobe (left middle cerebral artery territory), seen over several slices.",
        "clue": "The area is very bright on DWI (restricted diffusion). On FLAIR the same area is only faintly bright. Remember the image's right side is the patient's left.",
        "why": "Restricted diffusion means the brain tissue is acutely infarcting. A bright DWI with little FLAIR change suggests a recent stroke, which may still be treatable, so the stroke team needs to know immediately.",
        "series": [{"label": "DWI", "dir": "mat1/DWI"}, {"label": "FLAIR", "dir": "mat1/FLAIR"}],
        "reveal": {
            "series": [{"label": "DWI, marked", "dir": "mat1/DWI", "overlay_dir": "mat1/DWI_mask", "start": 38},
                       {"label": "FLAIR, marked", "dir": "mat1/FLAIR", "overlay_dir": "mat1/FLAIR_mask", "start": 38}],
            "lines": [
                "Nice catch! That bright patch on DWI is restricted diffusion in the left frontal lobe. It's an acute infarct.",
                "I've shaded the lesion for you. Scroll up and down: it runs over several slices in the left MCA territory.",
                "Now switch to FLAIR. Same spot, but only faintly bright. Bright DWI with a quiet FLAIR means the stroke is recent.",
                "Recent can mean treatable. On a real stroke call, every minute counts, so you tell the team straight away.",
            ],
        },
        "source": "isles2022",
    },
    {
        "id": "mat2", "opponent": "matilda", "modality": "MRI", "label": "MRI brain: T1, T1 post-contrast (T1+C), T2, FLAIR, SWI, DWI", "patient": "patient 0004",
        "history": "66-year-old man with headaches over a few weeks and new difficulty finding words.",
        "question": "What is the most likely diagnosis?",
        "options": ["High-grade glioma (glioblastoma)", "Acute ischaemic stroke", "Meningioma", "Subdural haematoma"],
        "answer": 0,
        "finding": "A mass in the left parietal lobe with a thick, irregular enhancing rim around a dark necrotic centre, and abnormal FLAIR signal spreading into the brain around it. Pathology confirmed glioblastoma, IDH-wildtype (WHO grade 4).",
        "clue": "On the post-contrast T1 the rim enhances irregularly and the middle does not (necrosis). FLAIR shows how far the abnormal signal spreads. The mass sits within the brain itself, unlike a meningioma, which grows from the dura on the brain's surface.",
        "why": "Glioblastoma is the commonest primary malignant brain tumour in adults and grows quickly. Swelling and mass effect can raise the pressure inside the skull, so it needs prompt referral to neurosurgery and oncology.",
        "series": [{"label": "T1", "dir": "mat2/T1"}, {"label": "T1+C", "dir": "mat2/T1c"}, {"label": "T2", "dir": "mat2/T2"}, {"label": "FLAIR", "dir": "mat2/FLAIR"}, {"label": "SWI", "dir": "mat2/SWI"}, {"label": "DWI", "dir": "mat2/DWI"}],
        "reveal": {
            "series": [{"label": "T1+C", "dir": "mat2/T1c", "overlay_dir": "mat2/T1c_mask", "start": 105},
                       {"label": "T1", "dir": "mat2/T1", "overlay_dir": "mat2/T1_mask", "start": 105},
                       {"label": "T2", "dir": "mat2/T2", "overlay_dir": "mat2/T2_mask", "start": 105},
                       {"label": "FLAIR", "dir": "mat2/FLAIR", "overlay_dir": "mat2/FLAIR_mask", "start": 105},
                       {"label": "SWI", "dir": "mat2/SWI", "overlay_dir": "mat2/SWI_mask", "start": 105},
                       {"label": "DWI", "dir": "mat2/DWI", "overlay_dir": "mat2/DWI_mask", "start": 105}],
            "lines": [
                "There it is, in the left parietal lobe. See that thick, ragged ring of enhancement on the post-contrast T1 (T1+C)? Compare it with the plain T1.",
                "The dark middle is necrosis: the tumour has outgrown its blood supply. That's a big hint it's high grade.",
                "Flip to T2 and FLAIR. The bright signal around it is tumour and swelling spreading into the brain. I've shaded the segmented tumour on every sequence.",
                "This one was confirmed as a glioblastoma. It needs the neurosurgeons and oncologists, fast.",
            ],
        },
        "source": "ucsfpdgm",
    },
    {
        "id": "mat3", "opponent": "matilda", "modality": "CT", "label": "CT head, non-contrast, axial",
        "history": "Adult on a blood thinner, found confused with sudden left-sided weakness and a severe headache.",
        "question": "What is the urgent finding?",
        "options": ["Acute intracerebral haemorrhage", "Acute ischaemic stroke", "Subdural haematoma", "Calcified brain tumour"],
        "answer": 0,
        "finding": "Acute intracerebral haemorrhage: a large, bright collection of fresh blood within the right side of the brain (on the image's left).",
        "clue": "On a non-contrast CT, fresh blood is bright (hyperdense). An ischaemic stroke is dark or may look normal early on, and a subdural haematoma is a crescent along the inside of the skull rather than inside the brain.",
        "why": "A bleed changes everything: no clot-busting treatment, urgent blood-pressure control, reversal of any blood thinner, and a neurosurgical opinion. The stroke team needs this result straight away.",
        "series": [{"label": "CT", "file": "mat3/ct.jpg"}],
        "reveal": {
            "series": [{"label": "Illustration", "file": "mat3/illustration.jpg"}, {"label": "CT", "file": "mat3/ct.jpg"}],
            "lines": [
                "Bright white on a non-contrast CT means fresh blood. Here it's a big bleed in the right side of the brain.",
                "Flip between the drawing and the CT: the red patch is the same bleed, sitting inside the brain tissue, not on its surface.",
                "An ischaemic stroke would look dark, not bright. A subdural would be a crescent hugging the skull.",
                "No clot-busters for this one! Blood pressure, reversing any blood thinner, neurosurgeons. Tell the team now.",
            ],
        },
        "downloads": [
            {"label": "original image (Wikimedia Commons)", "url": "https://upload.wikimedia.org/wikipedia/commons/0/03/1602_The_Hemorrhagic_Stroke-02.jpg"},
            {"label": "adapted CT panel (JPEG)", "file": "mat3/ct.jpg", "name": "Haemorrhagic-stroke_CT-panel_adapted-from-OpenStax_CC-BY-3.0.jpg"},
            {"label": "adapted illustration panel (JPEG)", "file": "mat3/illustration.jpg", "name": "Haemorrhagic-stroke_illustration-panel_adapted-from-OpenStax_CC-BY-3.0.jpg"},
        ],
        "source": "openstax_hstroke",
    },
    ph("mat4", "matilda", "MRI", "MRI brain, DWI"),
    ph("mat5", "matilda", "CT", "CT head, non-contrast"),
    {
        "id": "mat6", "opponent": "matilda", "modality": "MRI", "label": "MRI lumbar spine, sagittal fat-suppressed T2",
        "history": "Adult with worsening low back pain and fever, now with numbness between the legs, leg weakness and difficulty passing urine.",
        "question": "What is the urgent finding?",
        "options": ["Cauda equina syndrome from an epidural abscess", "Degenerative disc disease only", "Spondylolisthesis", "Normal lumbar spine"],
        "answer": 0,
        "finding": "Cauda equina compression: an epidural collection (abscess) in the lower lumbar canal compresses the thecal sac and the cauda equina nerve roots. High signal in the soft tissues behind the spine shows inflammation there too.",
        "clue": "Follow the bright CSF of the thecal sac down the canal. Where it is pinched and displaced by an abnormal collection, the nerve roots are being squeezed. With fever and new bladder or saddle symptoms, think infection and compression together.",
        "why": "Cauda equina syndrome is a surgical emergency: delays risk permanent leg weakness and loss of bladder, bowel and sexual function. The scan needs reporting and acting on straight away, and an abscess also needs antibiotics.",
        "series": [{"label": "Sagittal T2 FS", "file": "mat6/sag_t2fs.jpg"}],
        "reveal": {
            "series": [{"label": "Sagittal T2 FS", "file": "mat6/sag_t2fs.jpg"}],
            "lines": [
                "Follow the bright CSF down the canal. See where it gets pinched and pushed aside low down? That's the collection.",
                "It's an epidural abscess, squeezing the cauda equina nerve roots. Notice the bright, inflamed tissues behind the spine too.",
                "Back pain plus fever, numbness in the saddle area and bladder trouble: that's the story that should make you look here first.",
                "This is a race against time. Tell the team now, before those nerves stop working for good.",
            ],
        },
        "source": "chan_oh_ces",
    },
    # Hannah: abdominal and vascular emergencies
    {
        "id": "han1", "opponent": "hannah", "modality": "X-ray", "label": "Abdominal X-ray, supine",
        "history": "Older adult with several days of a swollen, painful abdomen, vomiting, and no bowel motions or wind.",
        "question": "What is the urgent finding?",
        "options": ["Large bowel obstruction", "Small bowel obstruction", "Pneumoperitoneum", "Normal bowel gas pattern"],
        "answer": 0,
        "finding": "Large bowel obstruction: the colon is markedly dilated, with gas-filled loops framing the edges of the abdomen and haustral folds that only partly cross the bowel.",
        "clue": "Large bowel sits around the outside of the abdomen and its haustra are thick and only partly cross the lumen. Small bowel sits centrally, with thin folds that cross the full width (the 'stack of coins'). A colon wider than about 6 cm (9 cm for the caecum) is dilated.",
        "why": "If the ileocaecal valve holds, the obstruction becomes a closed loop and the caecum can stretch until it perforates. The patient needs urgent surgical review, usually with CT to find the cause, such as a tumour or a volvulus.",
        "series": [{"label": "Supine AXR", "file": "han1/LargeBowelObsFlat2008.jpg"}],
        "reveal": {
            "series": [{"label": "Supine AXR", "file": "han1/LargeBowelObsFlat2008.jpg"}],
            "lines": [
                "Look at the frame: big, gas-filled loops running round the edge of the abdomen. That's colon, and it's very dilated.",
                "See the folds? They only go partway across the bowel. Haustra, not the full-width folds of small bowel.",
                "Large bowel obstruction. The big worry is the caecum stretching until it bursts.",
                "Surgical review, and usually a CT to find the cause. Feeling the pressure? So is that bowel. Move fast.",
            ],
        },
        "downloads": [{"label": "original image (Wikimedia Commons)", "url": "https://upload.wikimedia.org/wikipedia/commons/1/1f/LargeBowelObsFlat2008.jpg"}],
        "source": "heilman_lbo",
    },
    {
        "id": "han2", "opponent": "hannah", "modality": "CT", "label": "CT kidneys, ureters and bladder (non-contrast), axial", "patient": "image 23",
        "history": "Adult with left loin pain coming in waves, spreading to the groin, and blood in the urine.",
        "question": "What is the finding?",
        "options": ["Left renal calculi", "Right ureteric calculus", "Gallstones", "Normal study"],
        "answer": 0,
        "finding": "Stones in the collecting system of the left kidney. There is also a tiny stone in the right kidney.",
        "clue": "With no contrast given, stones are the brightest things in the kidney, almost as bright as bone. The cluster sits in the left kidney (on the image's right). Check the other kidney too.",
        "why": "Most kidney stones are managed without emergency treatment, but a stone that blocks the kidney is urgent, and a blocked kidney with infection is an emergency needing drainage. Look for a dilated collecting system and follow the ureter down to the bladder.",
        "series": [{"label": "Axial", "file": "han2/image23.jpg"}],
        "reveal": {
            "series": [{"label": "Axial, marked", "file": "han2/image23.jpg", "overlay": "han2/image23_mask.png"}],
            "lines": [
                "Spot on. Those bright clumps in the left kidney are stones sitting in the collecting system.",
                "No contrast was given, so anything that bright inside the kidney is calcium. Here, that means stones.",
                "Did you catch the tiny one in the right kidney too? Always check both sides.",
                "Next, look for a swollen, blocked kidney and follow the ureter down. A blocked, infected kidney can't wait.",
            ],
        },
        "source": "kidneystone_axial",
    },
    {
        "id": "han3", "opponent": "hannah", "modality": "CT", "label": "CT pulmonary angiogram, axial", "patient": "patient 7",
        "history": "Adult with sudden shortness of breath and sharp chest pain on breathing in.",
        "question": "What is the urgent finding?",
        "options": ["Bilateral pulmonary emboli", "Contrast mixing artefact, no embolus", "Aortic dissection", "Pneumonia"],
        "answer": 0,
        "finding": "Pulmonary emboli in both lungs: a large clot in the right pulmonary artery, extending into lobar and segmental branches on both sides.",
        "clue": "In the bright, contrast-filled pulmonary arteries, look for grey filling defects that keep their shape as you scroll through several slices. Mixing artefact fades and changes shape from slice to slice; a clot doesn't.",
        "why": "Pulmonary embolism can cause sudden collapse and death, especially when a large central clot strains the right side of the heart. The team needs the result straight away so treatment can start.",
        "series": [{"label": "CTPA", "dir": "han3/CTA"}],
        "reveal": {
            "series": [{"label": "CTPA, clots marked", "dir": "han3/CTA", "overlay_dir": "han3/CTA_mask", "start": 42}],
            "lines": [
                "There they are: grey clots sitting inside the bright pulmonary arteries. I've shaded the ones the radiologists marked.",
                "The big one is in the right pulmonary artery, near the heart. Scroll up and down and you'll find more on the left too.",
                "Real clots keep their shape slice after slice. Mixing artefact blurs and fades as you scroll.",
                "Clots on both sides, one of them central. That's a call to the team straight away, not a note in the queue.",
            ],
        },
        "source": "fumpe",
    },
    {
        "id": "han4", "opponent": "hannah", "modality": "CT", "label": "CT aortogram, axial", "patient": "patient 4",
        "history": "Adult with sudden tearing chest pain going through to the back.",
        "question": "What is the urgent finding?",
        "options": ["Stanford type A aortic dissection", "Stanford type B aortic dissection", "Abdominal aortic aneurysm", "Pulmonary embolism"],
        "answer": 0,
        "finding": "Aortic dissection involving the ascending aorta (Stanford type A), extending around the arch and down the descending and abdominal aorta.",
        "clue": "Scroll from the top. The aorta has two channels: a brightly enhancing true lumen and a crescent of lower-density false lumen beside it. The ascending aorta, just above the heart, is involved, which makes it type A.",
        "why": "Type A dissection is a surgical emergency. It can rupture, or extend into the coronary arteries or the aortic valve, and the risk of death rises by the hour without surgery. Phone the result through to the team immediately.",
        "series": [{"label": "CTA", "dir": "han4/CTA"}],
        "reveal": {
            "series": [{"label": "CTA, aorta marked", "dir": "han4/CTA", "overlay_dir": "han4/CTA_mask", "start": 28}],
            "lines": [
                "There it is. Look at the ascending aorta: a bright true lumen with a darker crescent wrapped around it. That's the false lumen.",
                "I've shaded the whole aorta so you can follow it. Scroll down and the false lumen keeps going, past the diaphragm and into the abdomen.",
                "The ascending aorta is involved, so it's Stanford type A. Type B spares the ascending aorta.",
                "Type A goes straight to the cardiothoracic surgeons. Pressure's on: phone it through now.",
            ],
        },
        "source": "aortaseg60",
    },
    {
        "id": "han5", "opponent": "hannah", "modality": "X-ray", "label": "Abdominal X-ray, supine (CT shown after a correct answer)",
        "history": "Older adult from a care home with a hugely swollen abdomen, colicky pain and no bowel motions for several days.",
        "question": "What is the urgent finding?",
        "options": ["Sigmoid volvulus", "Caecal volvulus", "Small bowel obstruction", "Pneumoperitoneum"],
        "answer": 0,
        "finding": "Sigmoid volvulus: the sigmoid colon has twisted on its mesentery, forming one huge gas-filled loop rising out of the pelvis (the coffee bean sign). CT shows the twist (the whirl sign) and the bowel tapering at it (the bird's beak sign).",
        "clue": "On the X-ray, look for a massive inverted-U loop of bowel rising out of the pelvis, its two walls meeting in the middle like a coffee bean. A caecal volvulus usually sits in the mid or left upper abdomen and looks more like a kidney bean, with small bowel dilated rather than colon.",
        "why": "The twist can cut off the bowel's blood supply, leading to ischaemia and perforation. It needs urgent surgical review; many are untwisted endoscopically, but signs of ischaemia mean surgery.",
        "series": [{"label": "AXR", "file": "han5/xray.jpg"}],
        "reveal": {
            "series": [{"label": "AXR", "file": "han5/xray.jpg"}, {"label": "CT axial", "file": "han5/ct_axial.jpg"}, {"label": "CT sagittal", "file": "han5/ct_sagittal.jpg"}],
            "lines": [
                "On the X-ray: one enormous loop rising out of the pelvis, its walls meeting in the middle. That's the coffee bean.",
                "Open the axial CT. See the swirl? The mesentery and vessels are twisted round on themselves: the whirl sign.",
                "Now the sagittal: the bowel narrows to a point right at the twist. That's the bird's beak.",
                "Coffee bean, whirl, bird's beak: one twisted sigmoid. Get the surgeons in before it loses its blood supply.",
            ],
        },
        "downloads": [
            {"label": "original figure (PMC)", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4317068/"},
            {"label": "adapted X-ray panel (JPEG)", "file": "han5/xray.jpg", "name": "Sigmoid-volvulus_X-ray-panel_adapted-from-Yigit-Turkdogan_CC-BY-2.0.jpg"},
            {"label": "adapted axial CT panel (JPEG)", "file": "han5/ct_axial.jpg", "name": "Sigmoid-volvulus_axial-CT-panel_adapted-from-Yigit-Turkdogan_CC-BY-2.0.jpg"},
            {"label": "adapted sagittal CT panel (JPEG)", "file": "han5/ct_sagittal.jpg", "name": "Sigmoid-volvulus_sagittal-CT-panel_adapted-from-Yigit-Turkdogan_CC-BY-2.0.jpg"},
        ],
        "source": "yigit_volvulus",
    },
    {
        "id": "han6", "opponent": "hannah", "modality": "CT", "label": "CT abdomen, portal venous phase, axial",
        "history": "Older adult with vague abdominal discomfort. Surprisingly, the abdomen is soft and the observations are normal.",
        "question": "What is the urgent finding?",
        "options": ["Pneumoperitoneum (free intraperitoneal air)", "Large bowel obstruction", "Pneumatosis intestinalis (gas in the bowel wall)", "Normal CT abdomen"],
        "answer": 0,
        "finding": "A large-volume pneumoperitoneum: free gas fills the front of the abdominal cavity, outside the bowel, and outlines the falciform ligament.",
        "clue": "With the patient lying flat, free air rises to sit under the anterior abdominal wall, outside the bowel loops. A lung window makes small amounts easier to see. Gas in the bowel wall (pneumatosis) instead follows the line of the bowel.",
        "why": "Free air usually means a perforated bowel and needs urgent surgical review. In this case the oral contrast scan showed no leak and the patient stayed well, so it was managed without surgery as an idiopathic pneumoperitoneum. That is the surgical team's decision to make, not a reason to delay escalating.",
        "series": [{"label": "Portal venous", "file": "han6/ct_portal_venous.jpg"}],
        "reveal": {
            "series": [{"label": "Portal venous", "file": "han6/ct_portal_venous.jpg"}, {"label": "Oral contrast", "file": "han6/ct_oral_contrast.jpg"}],
            "lines": [
                "See all that black at the front? That's air outside the bowel: a huge pneumoperitoneum. Look, it even outlines the falciform ligament.",
                "Free air normally means a hole in the gut, so the surgeons need to know straight away.",
                "Plot twist: open the oral contrast scan. No leak, and the patient stayed well. This one was idiopathic and managed without surgery.",
                "But that's the surgeons' call, not ours. Under pressure, you still escalate. Every time.",
            ],
        },
        "source": "liu_pneumoperitoneum",
    },
    # My-Vi: musculoskeletal
    {
        "id": "myv1", "opponent": "myvi", "modality": "X-ray", "label": "Right ankle, mortise view",
        "history": "Adult who rolled their ankle stepping off a kerb. Tender over the tip of the outer ankle bone.",
        "question": "The arrow marks the fibular fracture. How would you classify it?",
        "options": ["Weber A", "Weber B", "Weber C", "No fracture"],
        "answer": 0,
        "finding": "A Weber A fracture: the lateral malleolus is broken below the level of the ankle joint, so below the syndesmosis.",
        "clue": "Find the tibial plafond, the flat roof of the ankle joint, and compare. Weber A is below it, Weber B starts at it, and Weber C is above it. Then check the mortise: the gaps around the talus should be even.",
        "why": "With the syndesmosis intact, a Weber A fracture is usually stable and often managed in a boot. Still check the medial side and the medial clear space: widening means a less stable injury than it first looks.",
        "series": [{"label": "Mortise", "file": "myv1/weber_a_mortise.jpg"}],
        "reveal": {
            "series": [{"label": "Mortise", "file": "myv1/weber_a_mortise.jpg"}],
            "lines": [
                "Find the roof of the ankle joint, the tibial plafond. Now look at the fibular fracture: it's well below that line.",
                "Below the joint means below the syndesmosis. That's Weber A.",
                "The gaps around the talus are even, so the mortise looks intact. Usually a stable injury.",
                "Weber A, B, C: below, at and above the joint. Learn it once and every ankle gets easier.",
            ],
        },
        "source": "surmanowicz_weber",
    },
    {
        "id": "myv2", "opponent": "myvi", "modality": "X-ray", "label": "Knee, horizontal-beam (cross-table) lateral", "patient": "patient 3",
        "history": "Adult with a painful, swollen knee after a fall. Unable to bear weight.",
        "question": "What sign is this?",
        "options": ["Lipohaemarthrosis (fat-fluid level)", "Simple joint effusion", "Deep sulcus sign", "Segond fracture"],
        "answer": 0,
        "finding": "Lipohaemarthrosis: a straight fat-fluid level in the suprapatellar pouch, with fat floating on top of blood.",
        "clue": "Only a horizontal-beam (cross-table) lateral shows it. The beam runs parallel to the fluid level, so the lighter fat layer sits above the denser blood in a perfectly straight line. Fat in the joint means marrow has escaped from a bone.",
        "why": "Marrow fat can only get into the joint through a fracture that reaches the joint surface, so this sign means an intra-articular fracture even when you can't see one. Here the source describes a subtle tibial plateau fracture. Look hard for it; the patient may need CT.",
        "series": [{"label": "X-table lateral", "file": "myv2/lipohaemarthrosis_no_arrow.png"}],
        "reveal": {
            "series": [{"label": "X-table lateral, arrowed", "file": "myv2/lipohaemarthrosis_arrow.png"}],
            "lines": [
                "There: see that perfectly straight line in the pouch above the kneecap? My arrow's on it.",
                "Fat on top, blood underneath. That's a lipohaemarthrosis, and the fat came out of the bone marrow.",
                "Marrow fat only escapes through a fracture into the joint. Here it was a subtle tibial plateau fracture.",
                "You'll only catch this on a horizontal-beam lateral. Some breaks whisper; this one left a level.",
            ],
        },
        # links offered with the credit, as the licence advises
        "downloads": [
            {"label": "original image (Wikimedia Commons)", "url": "https://upload.wikimedia.org/wikipedia/commons/6/60/Lipohemarthrosis.png"},
            {"label": "adapted image, arrow removed (PNG)", "file": "myv2/lipohaemarthrosis_no_arrow.png",
             "name": "Lipohaemarthrosis_arrow-removed_adapted-from-James-Heilman_CC-BY-SA-3.0.png"},
        ],
        "source": "heilman_lipo",
    },
    {
        "id": "myv3", "opponent": "myvi", "modality": "X-ray", "label": "Wrist, lateral",
        "history": "Adult, fell onto an outstretched hand. Tender over the distal radius, no obvious deformity.",
        "question": "What sign is this?",
        "options": ["Pronator quadratus fat pad sign", "Spilled teacup sign", "Terry Thomas sign", "Sail sign"],
        "answer": 0,
        "finding": "Pronator quadratus fat pad sign: the thin fat stripe in front of the distal radius is bowed forwards, away from the bone (arrow).",
        "clue": "Normally this fat stripe lies flat and close to the front of the radius. Blood and swelling under the pronator quadratus muscle push it forwards.",
        "why": "It is an indirect sign of a distal radius fracture that can be very hard to see. The AP here shows an undisplaced fracture line running into the wrist joint. If the sign is present but no fracture is visible, treat it as a fracture and arrange follow-up imaging.",
        "series": [{"label": "Lateral", "file": "myv3/lateral.png"}],
        # shown after a correct answer, with the examiner talking it through
        "reveal": {
            "series": [{"label": "AP", "file": "myv3/ap.png"}],
            "lines": [
                "Now look at the AP view. Follow my arrow to the end of the radius.",
                "See that fine dark line running down into the wrist joint? An undisplaced fracture of the distal radius, extending into the joint.",
                "It barely shows on the AP. The lateral gave it away: bleeding under the pronator quadratus pushed the fat stripe off the bone.",
                "Some breaks whisper. That's why you read the soft tissues, not just the bones.",
            ],
        },
        "source": ["hellerhoff_pq_lat", "hellerhoff_pq_ap"],
    },
    {
        "id": "myv4", "opponent": "myvi", "modality": "X-ray", "label": "Ankle, lateral",
        "history": "Adult, twisted the left ankle stepping off a kerb. Swollen and tender over the outer ankle.",
        "question": "What is the injury?",
        "options": ["Distal fibula fracture", "Distal tibia fracture", "Calcaneal fracture", "No fracture"],
        "answer": 0,
        "finding": "A short oblique fracture of the distal fibula, just above the ankle joint.",
        "clue": "On the lateral view the fibula overlaps the back of the tibia. Look there for a fine oblique line and a small step or spike on the back edge of the fibula. On the AP view the same fracture is only a faint line.",
        "why": "Ankle fractures can be unstable, and a fibula fracture may come with a medial or ligament injury that is easy to miss. Check the mortise and the medial side, and make sure the patient has orthopaedic assessment before weight-bearing.",
        "series": [{"label": "Lateral", "file": "myv4/lateral_IMG0002348.jpg"}],
        "reveal": {
            "series": [
                {"label": "Lateral, marked", "file": "myv4/lateral_IMG0002348.jpg", "overlay": "myv4/lateral_IMG0002348_mask.png"},
                {"label": "AP, marked", "file": "myv4/ap_IMG0002347.jpg", "overlay": "myv4/ap_IMG0002347_mask.png"},
            ],
            "lines": [
                "Here it is. The fibula sits over the back of the tibia on a lateral view, and that is where the break hides.",
                "See the little spike on the fibula's back edge? That step is the fracture, running obliquely just above the joint.",
                "Now open the AP tab. The same break is there, but it's only a faint oblique line.",
                "Always read both views. A fracture can whisper on one and announce itself on the other.",
            ],
        },
        "source": "fracatlas",
    },
    {
        "id": "myv5", "opponent": "myvi", "modality": "X-ray", "label": "Right ankle, mortise view",
        "history": "Adult who twisted their ankle playing football. Swollen and tender over the outer ankle.",
        "question": "The arrow marks the fibular fracture. How would you classify it?",
        "options": ["Weber A", "Weber B", "Weber C", "No fracture"],
        "answer": 1,
        "finding": "A Weber B fracture: an oblique fracture of the distal fibula starting at the level of the ankle joint, at the syndesmosis.",
        "clue": "The fracture line begins level with the tibial plafond, the roof of the ankle joint, and runs obliquely upwards. At the joint means Weber B; below it would be A, and above it C.",
        "why": "Weber B fractures may be stable or unstable. The deciding factor is the medial side: if the medial clear space is widened (or the medial malleolus is broken), the ankle is unstable and usually needs surgery.",
        "series": [{"label": "Mortise", "file": "myv5/weber_b_mortise.jpg"}],
        "reveal": {
            "series": [{"label": "Mortise", "file": "myv5/weber_b_mortise.jpg"}],
            "lines": [
                "Trace the fibular fracture to where it starts: right at the level of the joint roof. That's the syndesmosis.",
                "At the joint is Weber B. Below would be A, above would be C.",
                "Now the important bit: check the medial clear space. Here it's normal, but if it widens, this one is unstable.",
                "Some breaks whisper; this one asks a question. Always check the other side of the ankle for the answer.",
            ],
        },
        "source": "surmanowicz_weber",
    },
    {
        "id": "myv6", "opponent": "myvi", "modality": "X-ray", "label": "Right hand, PA",
        "history": "Young adult with a painful, swollen hand after punching a wall.",
        "question": "The arrow points to the fracture. What is this type of fracture commonly known as?",
        "options": ["Boxer's fracture", "Bennett's fracture", "Rolando fracture", "Colles' fracture"],
        "answer": 0,
        "finding": "Boxer's fracture: a fracture of the neck of the fifth metacarpal (the little-finger side), with the head tipped towards the palm.",
        "clue": "Follow the little finger's metacarpal back from the knuckle: the neck is angled and its cortex broken just behind the head. Bennett's and Rolando fractures involve the base of the thumb metacarpal, and a Colles' fracture is at the wrist.",
        "why": "It usually comes from punching something hard. Check how angled it is and whether the finger is rotated, and look for a wound over the knuckle: a cut from a tooth (a 'fight bite') needs urgent washout and antibiotics.",
        "series": [{"label": "PA", "file": "myv6/hand_pa.jpg"}],
        "reveal": {
            "series": [{"label": "PA", "file": "myv6/hand_pa.jpg"}],
            "lines": [
                "Little finger, just behind the knuckle: the neck of the fifth metacarpal is broken and the head is tipped towards the palm.",
                "That's a boxer's fracture, named after the punch that usually causes it.",
                "Bennett's and Rolando fractures live at the base of the thumb. Colles' is down at the wrist. Know your names!",
                "And always check that knuckle for a cut. A tooth wound from a punch can turn a simple break into a nasty infection.",
            ],
        },
        "source": "kaggle_fracture_multiregion",
    },
    # The Lightbox (champion): mixed
    {
        "id": "lbx1", "opponent": "lightbox", "modality": "CT", "label": "CT cervical spine, axial (C1) and coronal",
        "history": "Adult who dived into a shallow pool and hit the top of their head. Neck pain, no weakness or numbness.",
        "question": "What is this injury called?",
        "options": ["Jefferson fracture (C1 burst)", "Hangman's fracture (C2)", "Odontoid peg fracture", "Clay-shoveler's fracture"],
        "answer": 0,
        "finding": "A Jefferson fracture: a burst fracture of the atlas (C1), with breaks through the anterior arch and a fracture of the right lateral mass, and mild lateral spread of the lateral masses.",
        "clue": "A vertical blow through the top of the head drives the skull down onto C1 and bursts the ring apart. On the axial, look for breaks in the ring of C1. On the coronal, check whether the lateral masses overhang C2: a large combined overhang suggests the transverse ligament has torn and the injury is unstable.",
        "why": "Whether it is stable depends on the transverse atlantal ligament, so these patients stay immobilised until it is assessed, often with MRI. This patient's ligament was intact and they were treated in a hard collar without any neurological problems.",
        "series": [{"label": "Axial (C1)", "file": "lbx1/ct_axial_c1.jpg"}, {"label": "Coronal", "file": "lbx1/ct_coronal.jpg"}],
        "reveal": {
            "series": [{"label": "Axial (C1)", "file": "lbx1/ct_axial_c1.jpg"}, {"label": "Coronal", "file": "lbx1/ct_coronal.jpg"}],
            "lines": [
                "A ring of bone can't break in just one place. See the arrows? C1's anterior arch is cracked through.",
                "Flip to the coronal. The right lateral mass is broken too, and both masses are sliding out past C2.",
                "A blow straight down on the head, bursting the atlas open. That's a Jefferson fracture.",
                "Collar on and keep them still until the ligament's checked. I've seen a lot of necks on my screen; this one deserved respect.",
            ],
        },
        "source": "martinez_jefferson",
    },
    {
        "id": "lbx2", "opponent": "lightbox", "modality": "X-ray", "label": "Skull, lateral (infant)",
        "history": "Infant who rolled off a changing table, now with a soft swelling on the side of the head.",
        "question": "What is the finding?",
        "options": ["Depressed skull fracture", "Linear skull fracture", "Normal cranial suture", "Vascular groove"],
        "answer": 0,
        "finding": "A depressed skull fracture of the vault: a segment of bone is pushed inwards, seen as a curved line where the edges overlap.",
        "clue": "Where a fragment is pushed in, its edge overlaps the neighbouring bone, so the line looks denser rather than darker. A simple linear fracture is a sharp dark line. Sutures zig-zag in predictable places, and vascular grooves branch and taper.",
        "why": "A depressed fragment can tear the dura or press on the brain, so it needs CT and a neurosurgical opinion. In an infant, also make sure someone asks how the injury happened.",
        "series": [{"label": "Lateral", "file": "lbx2/no_arrow.png"}],
        "reveal": {
            "series": [{"label": "Lateral, arrowed", "file": "lbx2/original_arrow.jpg"}],
            "lines": [
                "Lights on. See where my arrow points? That curved line is the edge of a piece of bone pushed inwards.",
                "Where the pieces overlap, bone sits on bone, so the line looks denser, not darker. That's how you know it's depressed, not just a crack.",
                "Sutures zig-zag in places you can predict, and vascular grooves branch. This does neither.",
                "Next stop: CT and the neurosurgeons. And in a baby, always ask how it happened. I've hung on enough ward walls to know.",
            ],
        },
        "downloads": [
            {"label": "original image (Wikimedia Commons)", "url": "https://upload.wikimedia.org/wikipedia/commons/8/8f/Skull_Fracture.jpg"},
            {"label": "adapted image, arrow removed (PNG)", "file": "lbx2/no_arrow.png", "name": "Depressed-skull-fracture_arrow-removed_public-domain_NIH.png"},
        ],
        "source": "nih_skull",
    },
    ph("lbx3", "lightbox", "CT", "CT abdomen and pelvis"),
    ph("lbx4", "lightbox", "X-ray", "Shoulder, AP"),
    ph("lbx5", "lightbox", "MRI", "MRI brain"),
    ph("lbx6", "lightbox", "X-ray", "Abdominal X-ray"),
]

# Image source attribution, keyed by each case's "source".
SOURCES = {
    "martinez_jefferson": {
        "short": "Martinez-Romo & McCoy (2021), J Educ Teach Emerg Med",
        "citation": "Martinez-Romo MA, McCoy CE. Jefferson Fracture and the Classification System for Atlas Fractures, A Case Report. "
                    "J Educ Teach Emerg Med. 2021;6(2):V16-V19. Figures 1 and 3.",
        "url": "https://doi.org/10.21980/J88P9C",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "converted to greyscale JPEG for display; the authors' arrows kept",
    },
    "liu_pneumoperitoneum": {
        "short": "Liu, Auld & Stieler (2026), Cureus",
        "citation": "Liu Y, Auld M, Stieler G. The Silent Abdomen: The Conservative Management of Large Idiopathic Pneumoperitoneum. Cureus. 2026;18(5):e109171. Figures 1 and 3.",
        "url": "https://doi.org/10.7759/cureus.109171",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "converted to greyscale JPEG for display",
    },
    "tritsch_tension": {
        "short": "Tritsch, Galan & Oates (2021), J Educ Teach Emerg Med",
        "adapted": True,
        "citation": "Tritsch Z, Galan G, Oates G. Case Report: Traumatic Tension Pneumothorax in a Pediatric Patient. J Educ Teach Emerg Med. 2021;6(1).",
        "url": "https://doi.org/10.5070/M561051823",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "the red line and blue arrows were digitally removed from the first image shown (the annotated image is the original); converted for display",
    },
    "ware_coinstack": {
        "short": "Ware et al. (2026), J Educ Teach Emerg Med",
        "citation": "Ware PJ, Ware C, Bjornstad AH, Kuntz HM, Young TP. A Case Report of a Coin Stack Masquerading as a Button Battery. "
                    "J Educ Teach Emerg Med. 2026;11(3):V31-V34. Figures 1 and 2.",
        "url": "https://doi.org/10.5070/M5.53886",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "converted to JPEG and resized for display; the authors' green arrow and stick-figure annotations kept",
    },
    "hellerhoff_ett": {
        "short": "Hellerhoff, Wikimedia Commons",
        "citation": "Hellerhoff (2022). Tubusspitze im rechten Hauptbronchus 64W - CR ap - 001. Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:Tubusspitze_im_rechten_Hauptbronchus_64W_-_CR_ap_-_001.jpg",
        "licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "changes": "converted to greyscale JPEG and resized for display",
    },
    "hellerhoff_ett_ann": {
        "short": "Hellerhoff, Wikimedia Commons",
        "citation": "Hellerhoff (2022). Tubusspitze im rechten Hauptbronchus 64W - CR ap - 001 - Annotation. Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:Tubusspitze_im_rechten_Hauptbronchus_64W_-_CR_ap_-_001_-_Annotation.jpg",
        "licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "changes": "resized for display",
    },
    "yigit_volvulus": {
        "short": "Yigit & Turkdogan (2014), Pan Afr Med J",
        "adapted": True,
        "citation": "Yigit M, Turkdogan KA. Coffee bean sign, whirl sign and bird's beak sign in the diagnosis of sigmoid volvulus. Pan Afr Med J. 2014;19:56. Figure 1.",
        "url": "https://doi.org/10.11604/pamj.2014.19.56.5142",
        "licence": "CC BY 2.0", "licence_url": "https://creativecommons.org/licenses/by/2.0/",
        "changes": "the three-panel figure was split into its X-ray panel (shown first) and its axial and sagittal CT panels (shown after a correct answer); panel letters removed; the original arrows kept",
    },
    "heilman_lbo": {
        "short": "James Heilman, MD, Wikimedia Commons",
        "citation": "James Heilman, MD. LargeBowelObsFlat2008. Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:LargeBowelObsFlat2008.jpg",
        "licence": "CC BY-SA 3.0", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/",
        "changes": "converted to greyscale JPEG and resized for display",
    },
    "surmanowicz_weber": {
        "short": "Surmanowicz et al. (2025), Diagnostics",
        "citation": "Surmanowicz P, Hamilton AM, Mondal P, Kulyk P, Sahota N, Obaid H. Correlation Between Weber Classification of Ankle Fractures and Medial Clear Space Widening on Radiography. "
                    "Diagnostics. 2025;15(16):2085. Figures 1 and 2.",
        "url": "https://doi.org/10.3390/diagnostics15162085",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "converted to greyscale JPEG for display",
    },
    "kaggle_fracture_multiregion": {
        "short": "Rodrigo (2024), Bone Fracture Multi-Region X-ray Data, Kaggle",
        "citation": "Madushani Rodrigo (2024). Bone Fracture Multi-Region X-ray Data [Data set]. Kaggle.",
        "url": "https://www.kaggle.com/datasets/bmadushanirodrigo/fracture-multi-region-x-ray-data",
        "licence": "ODC Public Domain Dedication and Licence (PDDL) 1.0", "licence_url": "https://opendatacommons.org/licenses/pddl/1-0/",
        "changes": "black side borders cropped; converted to JPEG for display. No attribution is required under the PDDL; the source is listed so the image can be traced",
    },
    "openstax_hstroke": {
        "short": "OpenStax College, Anatomy & Physiology, Wikimedia Commons",
        "adapted": True,
        "citation": "OpenStax College (2013). 1602 The Hemorrhagic Stroke-02. Anatomy & Physiology, Connexions Web site, http://cnx.org/content/col11496/1.6/. Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:1602_The_Hemorrhagic_Stroke-02.jpg",
        "licence": "CC BY 3.0", "licence_url": "https://creativecommons.org/licenses/by/3.0/",
        "changes": "the two-panel figure was split into its CT panel (shown first, converted to greyscale) and its illustration panel (shown after a correct answer), and the (a)/(b) labels cropped off; converted to JPEG",
    },
    "chan_oh_ces": {
        "short": "Chan & Oh (2016), Int J Emerg Med",
        "citation": "Chan, J., Oh, J.J. A rare case of multiple spinal epidural abscesses and cauda equina syndrome presenting to the emergency department following acupuncture. "
                    "Int J Emerg Med 9, 22 (2016). Figure from the article.",
        "url": "https://doi.org/10.1186/s12245-016-0116-5",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "converted to greyscale JPEG for display",
    },
    "nih_skull": {
        "short": "National Institutes of Health, Wikimedia Commons (public domain)",
        "adapted": True,
        "citation": "National Institutes of Health. Skull Fracture (depressed skull fracture in an infant). Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:Skull_Fracture.jpg",
        "licence": "Public domain", "licence_url": "https://commons.wikimedia.org/wiki/File:Skull_Fracture.jpg",
        "changes": "the arrow was digitally removed from the first image shown (the arrowed image is the original); converted to greyscale JPEG for display. "
                   "No attribution is required; the source is listed so the image can be traced",
    },
    "docjames_battery": {
        "short": "Doc James, Wikimedia Commons",
        "adapted": True,
        "citation": "Doc James (2024). ButtonBatteryIngestion. Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:ButtonBatteryIngestion.png",
        "licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "changes": "the red arrow was digitally removed from the first image shown (filled in to match the surrounding film); the arrowed image is the original; "
                   "both converted to greyscale JPEG for display. These adaptations are shared under the same licence, CC BY-SA 4.0",
    },
    "hellerhoff_pmed": {
        "short": "Hellerhoff, Wikimedia Commons",
        "adapted": True,
        "citation": "Hellerhoff (2015). Mediastinalemphysem - Roe vs CT LF. Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:Mediastinalemphysem_-_Roe_vs_CT_LF.jpg",
        "licence": "CC BY-SA 3.0", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/",
        "changes": "the side-by-side original was split into its X-ray panel (shown first, arrows kept) and its CT panel (shown after a correct answer); "
                   "converted to JPEG for display. These adaptations are shared under the same licence, CC BY-SA 3.0",
    },
    "heilman_lipo": {
        "short": "James Heilman, MD, Wikimedia Commons",
        "adapted": True,
        "citation": "James Heilman, MD (2011). Lipohemarthrosis. Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:Lipohemarthrosis.png",
        "licence": "CC BY-SA 3.0", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/",
        "changes": "the arrow was removed from the first image shown (the arrowed image is the original); both converted to greyscale JPEG for display. "
                   "These adaptations are shared under the same licence, CC BY-SA 3.0",
    },
    "fumpe": {
        "short": "Masoudi & Saadatmand-Tarzjan (2018), FUMPE, figshare",
        "citation": "Masoudi, M., & Saadatmand-Tarzjan, M. (2018). FUMPE: Ferdowsi University of Mashhad's PE dataset [Data collection]. figshare. "
                    "Images: Patient 7; ground truth by two radiologists.",
        "url": "https://doi.org/10.6084/m9.figshare.c.4107803.v1",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "averaged into 2 mm axial slabs, windowed (700/100) and resized; the dataset's ground-truth clot mask drawn as an overlay",
    },
    "ucsfpdgm": {
        "short": "Calabrese et al. (2022), UCSF-PDGM (v5), The Cancer Imaging Archive",
        "citation": "Calabrese, E., Villanueva-Meyer, J., Rudie, J., Rauschecker, A., Baid, U., Bakas, S., Cha, S., Mongan, J., Hess, C. (2022). "
                    "The University of California San Francisco Preoperative Diffuse Glioma MRI (UCSF-PDGM) (Version 5) [dataset]. The Cancer Imaging Archive.",
        "url": "https://doi.org/10.7937/tcia.bdgf-8v37",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "T1, T1 post-contrast, T2, FLAIR, SWI and DWI, all 155 axial slices (1 mm), windowed to 8-bit and cropped; tumour segmentation drawn as an overlay; diagnosis from the collection's clinical metadata",
    },
    "kidneystone_axial": {
        "short": "Abdalla, Mahmood & Hama (2025), Mendeley Data",
        "citation": "Abdalla, P. A., Mahmood, B. S., & Hama, N. R. (2025). Axial CT Imaging Dataset for AI-Powered Kidney Stone Detection: "
                    "A Resource for Deep Learning Research. Mendeley Data, V1.",
        "url": "https://doi.org/10.17632/fwhytt5mzd.1",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "converted to greyscale JPEG; stones outlined as an overlay (drawn for this game, not part of the dataset)",
    },
    "aortaseg60": {
        "short": "El Rahal, Rotzinger & Fahrni (2026), AortaSeg-60, Zenodo",
        "citation": "El Rahal, D., Rotzinger, D. C., & Fahrni, G. (2026). AortaSeg-60 (Version 1.1) [Data set]. Zenodo.",
        "url": "https://doi.org/10.5281/zenodo.18147026",
        "licence": "CC0 1.0", "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "changes": "averaged into 3 mm axial slabs, windowed and resized; the dataset's aorta segmentation drawn as an overlay",
    },
    "isles2022": {
        "short": "Hernandez Petzsche et al. (2022), ISLES 2022, Zenodo",
        "citation": "Hernandez Petzsche, M. R., de la Rosa, E., Wiest, R., Hanning, U., Wiestler, B., & Kirschke, J. S. (2022). "
                    "ISLES 2022: A multi-center magnetic resonance imaging stroke lesion segmentation dataset [Data set]. Zenodo. "
                    "Described in Scientific Data, doi:10.1038/s41597-022-01875-5.",
        "url": "https://doi.org/10.5281/zenodo.7153326",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "FLAIR resampled onto the DWI's axial planes, windowed to 8-bit and cropped; lesion mask drawn as an overlay",
    },
    "fracatlas": {
        "short": "Abedeen et al. (2023), FracAtlas, figshare",
        "citation": "Abedeen, I., Rahman, M. A., Zohra Prottyasha, F., Ahmed, T., Mohmud Chowdhury, T., & Shatabda, S. (2023). "
                    "FracAtlas: A Dataset for Fracture Classification, Localization and Segmentation of Musculoskeletal Radiographs. figshare. Dataset.",
        "url": "https://doi.org/10.6084/m9.figshare.22363012",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "converted to greyscale JPEG and resized; the dataset's fracture annotation drawn as an overlay",
    },
    "ptx498": {
        "short": "Wang (2021), PTX-498, Zenodo",
        "citation": "Wang, Y. (2021). PTX-498: A multi-center pneumothorax segmentation chest X-ray image dataset [Data set]. "
                    "In Neurocomputing (Version v2-fix, Vol. 454, pp. 201-211). Zenodo.",
        "url": "https://doi.org/10.5281/zenodo.8266529",
        "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "changes": "converted to greyscale JPEG; segmentation mask rendered as a coloured overlay",
    },
    "hellerhoff_pq_lat": {
        "short": "Hellerhoff, Wikimedia Commons",
        "citation": "Hellerhoff. Pronator quadratus - fatpad-sign pathologisch bei Fraktur Erwachsener (2010). Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:Pronator_quadratus_-_fatpad-sign_pathologisch_bei_Fraktur_Erwachsener.png",
        "licence": "CC BY-SA 3.0", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/",
        "changes": "converted to JPEG",
    },
    "hellerhoff_pq_ap": {
        "short": "Hellerhoff, Wikimedia Commons",
        "citation": "Hellerhoff. Distale Radiusfraktur laengs zu Fatpadsign erwachsen. Wikimedia Commons.",
        "url": "https://commons.wikimedia.org/wiki/File:Distale_Radiusfraktur_laengs_zu_Fatpadsign_erwachsen.png",
        "licence": "CC BY-SA 3.0", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/",
        "changes": "converted to JPEG",
    },
    # "example": {
    #     "citation": "Author (Year). Title. Publisher.",
    #     "url": "https://doi.org/...",
    #     "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
    #     "changes": "converted to greyscale JPEG",
    # },
}

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def natural(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def series_files(s):
    if "file" in s:
        return [A / "src" / s["file"]]
    files = sorted((f for f in (A / "src" / s["dir"]).iterdir() if f.suffix.lower() in IMG_EXT), key=natural)
    return files[::-1] if s.get("reverse") else files


def has_colour(im):
    """True if the image has coloured annotation (an arrow, say), so it should not be greyscaled."""
    sm = im.copy(); sm.thumbnail((256, 256))
    b = sm.tobytes()
    return any(max(b[i:i + 3]) - min(b[i:i + 3]) > 40 for i in range(0, len(b), 3))


OV_FILL, OV_EDGE = (255, 70, 90), (255, 230, 120)   # same look as Pneumo Patrol / Spot the Pneumothorax


def make_overlay(mask_path, size, out_path):
    """White-on-black mask -> transparent PNG: tinted fill plus a bright outline of the edge."""
    m = Image.open(mask_path).convert("L").resize(size, Image.LANCZOS)
    m = m.point(lambda v: 255 if v > 127 else 0).filter(ImageFilter.MedianFilter(5))
    edge = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(7)), m.filter(ImageFilter.MinFilter(3)))
    out = Image.new("RGBA", m.size, OV_FILL + (0,))
    out.putalpha(m.point(lambda v: int(v * 0.42)))
    e = Image.new("RGBA", m.size, OV_EDGE + (0,)); e.putalpha(edge)
    Image.alpha_composite(out, e).save(out_path, optimize=True)
    return out_path


def data_uri(p):
    mime = {".png": "image/png", ".webp": "image/webp"}.get(p.suffix, "image/jpeg")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def check(c):
    errs = []
    if c["opponent"] not in OPPONENTS: errs.append(f"unknown opponent {c['opponent']!r}")
    if len(c["options"]) != 4: errs.append(f"needs 4 options, has {len(c['options'])}")
    if not 0 <= c["answer"] < len(c["options"]): errs.append("answer index out of range")
    if len(set(c["options"])) != len(c["options"]): errs.append("duplicate options")
    if not c.get("placeholder") and not c["series"]: errs.append("no series (add images or mark it a placeholder)")
    for k in (c["source"] if isinstance(c.get("source"), list) else [c.get("source")]):
        if k and k not in SOURCES: errs.append(f"unknown source {k!r}")
    return errs


def main():
    preview = "--preview" in sys.argv
    bad = False
    for c in CASES:
        for e in check(c):
            print(f"!! {c['id']}: {e}"); bad = True
    for o in OPPONENTS:
        n = sum(c["opponent"] == o for c in CASES)
        if n != 6: print(f"!! {o} has {n} case(s); the game expects 6"); bad = True
    if bad: sys.exit(1)

    pool, pool_ix = [], {}
    def ref(uri):
        if preview: return uri
        if uri not in pool_ix: pool_ix[uri] = len(pool); pool.append(uri)
        return pool_ix[uri]

    def convert(c, series, prefix):
        out = []
        for si, s in enumerate(series):
            files = series_files(s)
            if not files: sys.exit(f"!! {c['id']}: series {s['label']!r} has no images")
            side = XRAY_SIDE if len(files) == 1 else STACK_SIDE
            d = A / "cases" / c["id"]; d.mkdir(parents=True, exist_ok=True)
            imgs = []
            for k, f in enumerate(files):
                im = Image.open(f).convert("RGB")
                if not has_colour(im): im = im.convert("L")
                if max(im.size) > side: im.thumbnail((side, side), Image.LANCZOS)
                p = d / f"{prefix}{si}_{k:03d}.jpg"
                im.save(p, "JPEG", quality=88 if len(files) == 1 else 74, optimize=True)
                imgs.append(f"assets/cases/{c['id']}/{p.name}" if preview else ref(data_uri(p)))
            entry = {"label": s["label"], "images": imgs}
            if "start" in s: entry["start"] = s["start"]
            if s.get("overlay_dir"):
                mfiles = sorted((f for f in (A / "src" / s["overlay_dir"]).iterdir() if f.suffix.lower() in IMG_EXT), key=natural)
                if len(mfiles) != len(files): sys.exit(f"!! {c['id']}: {s['overlay_dir']} has {len(mfiles)} masks for {len(files)} slices")
                ovs = []
                for k, mf in enumerate(mfiles):
                    if Image.open(mf).convert("L").getextrema()[1] < 128: ovs.append(None); continue   # nothing on this slice
                    op = make_overlay(mf, Image.open(files[k]).size, d / f"{prefix}{si}_ov{k:03d}.png")
                    ovs.append(f"assets/cases/{c['id']}/{op.name}" if preview else ref(data_uri(op)))
                entry["overlays"] = ovs
            if s.get("overlay"):
                if len(files) != 1: sys.exit(f"!! {c['id']}: an overlay needs a single-image series")
                op = make_overlay(A / "src" / s["overlay"], im.size, d / f"{prefix}{si}_overlay.png")
                entry["overlays"] = [f"assets/cases/{c['id']}/{op.name}" if preview else data_uri(op)]
            out.append(entry)
        return out

    out_cases = []
    for c in CASES:
        e = {k: v for k, v in c.items() if k not in ("series", "reveal")}
        e["series"] = convert(c, c["series"], "s")
        if c.get("reveal"):
            e["reveal"] = {"lines": c["reveal"]["lines"], "series": convert(c, c["reveal"]["series"], "r")}
        if c.get("downloads"):     # local files are offered as-is (lossless), not the display JPEG
            e["downloads"] = [{"label": d["label"], "name": d.get("name"),
                               "url": d["url"] if "url" in d else (f"assets/src/{d['file']}" if preview else ref(data_uri(A / "src" / d["file"])))}
                              for d in c["downloads"]]
        out_cases.append(e)

    used = set()
    for c in CASES:
        src = c.get("source")
        used.update(src if isinstance(src, list) else [src] if src else [])
    sources = {k: v for k, v in SOURCES.items() if k in used}
    assets = {"logo_mark": data_uri(A / "logo_mark.png"), "art": {}}
    for f in sorted((A / "art").glob("*_*.webp")):          # battle poses cut by tools/cut_poses.py
        who, pose = f.stem.split("_", 1)
        assets["art"].setdefault(who, {})[pose] = f"assets/art/{f.name}" if preview else data_uri(f)
    src = (ROOT / "game.html").read_text(encoding="utf-8")
    out = (src.replace("/*__CASES__*/[]", json.dumps(out_cases))
              .replace("/*__SOURCES__*/{}", json.dumps(sources))
              .replace("/*__ASSETS__*/{}", json.dumps(assets))
              .replace("/*__POOL__*/[]", json.dumps(pool)))
    names = ["_preview.html"] if preview else ["index.html", "critical-four.embed.html"]
    for n in names:
        (ROOT / n).write_text(out, encoding="utf-8")
    for o in OPPONENTS:
        cs = [c for c in CASES if c["opponent"] == o]
        real = sum(not c.get("placeholder") for c in cs)
        print(f"{o:9s} {len(cs)} cases, {real} real, {len(cs) - real} placeholder")
    print(f"-> {', '.join(names)}, {len(out) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
