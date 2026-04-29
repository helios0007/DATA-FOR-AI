# Problem Brief — [Passive Design Advisor: Barcelona 2025]

> Copy this file into your team's repo as `docs/problem-brief.md`.
> Fill in every section. One page total. Plain English. Today.
>
> This is your project's **purpose document.** Every other deliverable
> in the seminar references this. Get it right and the rest gets easier.

---

## The Environmental Question

*One or two sentences. What environmental or ecosystem-related question
are you answering with data?*

> Example: *How fast is Barceloneta beach eroding, and which seafront
> buildings will be most exposed to wave action and storm surge by 2031?*

**Your question:**

[ Which outdoor climate conditions (temperature, humidity, wind speed and
direction, solar radiation) in central Barcelona most strongly predict
indoor thermal discomfort — and which passive design strategies most
effectively close that gap, by building typology and neighbourhood,
in summer 2025? ]

---

## The Design Decision This Supports

*A real decision someone will make, more confidently because of your
project. Not "raise awareness." A specific, near-term action.*

> Example: *The Barcelona Urban Resilience Office is preparing the 2026–2030
> capital plan. They need to decide which seafront buildings get priority
> funding for adaptation works.*

**Your decision:**

[ An architect or urban environmental analyst is evaluating an existing
or proposed building in central Barcelona and needs to decide which
passive design interventions — shading, cross-ventilation, thermal
mass, orientation adjustments — are worth pursuing before resorting
to active systems. This project gives them a data-grounded
recommendation, specific to their building's typology and location,
rather than relying on generic guidelines.
Two decisions are supported in sequence:

Diagnostic: Where does passive design currently fail in central
Barcelona, and for which typologies? (The analysis layer.)

Prescriptive: Given a specific building context, which passive
strategies are most likely to reduce the outdoor-to-indoor thermal
gap? (The tool layer.)]

---

## The Intended User

*Who is the person reading your output? What's their role? What do they
already know? What do they not know?*

> Example: *Capital planning analyst at the Barcelona Urban Resilience
> Office. Familiar with GIS and municipal data. Not a coastal engineer.
> Needs an output they can defend in front of district councilors.*

**Your user:**

[ Architect or urban environmental analyst working in Barcelona.]

---

## Measurable Success Criteria

*3–5 things that, if true at the end, mean the project worked. Each one
must be checkable. "Useful" is not checkable; "<10 buildings on the
shortlist" is.*

> Example:
> 1. Reproducible from the repo by a non-author in <10 minutes
> 2. 2031 coastline projection within ±2 m of an external validation
> 3. Tier 1 shortlist of <10 buildings, includes the 3 already flagged by engineers
> 4. Model card and failure gallery clear enough that a councilor can
>    state what the system can and cannot do

**Your criteria:**

1. [The analysis pipeline is reproducible from the repo by a non-author
in under 15 minutes using only open data sources.]
2. [The tool accepts a minimum of 3 user inputs (neighbourhood,
building typology, orientation) and returns a ranked list of at
least 3 passive design strategies with an expected impact score.]
3. [Strategy recommendations are traceable back to the data — each
one links to the climate variable or typology pattern that
justifies it.]

---

## Risks and Open Questions

*What could make this project fail? What do you not know yet that you
need to learn?*

**Risks:**

- [The tool's recommendations may oversimplify passive design logic
if the data sample is too small to distinguish typologies reliably.]
- [Summer 2025 data may still be incomplete or require significant
cleaning effort.]

**Open questions for next session:**

- [What is the minimum building sample size needed to make typology
rankings statistically defensible?]
- [How do we define "passive design failure" in a way that is both
technically grounded and legible to an architect?]
- [What form does the tool take — a web interface, a notebook, a
Grasshopper component?]

---

## Out of Scope

*What are you NOT doing? Be explicit. This protects you from scope creep.*

- [We are NOT conducting primary data collection (installing sensors,
running surveys).]
- [We are NOT covering buildings outside central Barcelona
neighbourhoods.]
- [We are NOT building a real-time monitoring dashboard — the tool
uses historical and current open data, not live feeds.]

---

## Team

| Name | Role on this project |
|---|---|
| [Gaelle Habib] | [tbc] |
| [Chun-Chun Chang] | [tbc] |
| [Nithik Vairamuthu] | [tbc] |
| [Vimal TN] | [tbc] |

> Roles are loose — they help you divide work, not lock you in. Everyone
> reads everyone's code. Everyone defends every line.


github - https://github.com/helios0007/DATA-FOR-AI

miro - https://miro.com/welcomeonboard/RHgrOXkxK2x4MzNXR1JqbmJIRG5veWg0MDdhbDhLLzZmMXZoUVdkM1l0RnhSRSs3YkNDNGVSc3JrZExNOE1lRWlSMmMwcjdBTTRBbDM4UWdkK0JFNGZ5M1UvTnZDSXVoV05qVVBXTkdIM3MySWxKZS9pTXE3R1VRbTdQbEIxRFpBS2NFMDFkcUNFSnM0d3FEN050ekl3PT0hdjE=?share_link_id=481768122950

