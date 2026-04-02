"""
Seed script for the 5 initial benchmark cases.
Run once after the migration:

    cd backend
    python -m app.data.benchmark_cases_seed

"""
from datetime import datetime
from app.database import SessionLocal
from app.models.benchmark import BenchmarkCase

CASES = [
    {
        "slug": "new_coke_1985",
        "title": "New Coke Launch (1985)",
        "category": "product_launch",
        "description": (
            "In April 1985, Coca-Cola replaced its 99-year-old formula with a sweeter version "
            "dubbed 'New Coke'. The decision followed blind taste tests suggesting consumers "
            "preferred the new formula over both old Coke and Pepsi. The public reaction was "
            "swift and severe — Coca-Cola received over 400,000 complaint calls and letters. "
            "By July 1985, just 79 days after launch, the company reversed course and brought "
            "back 'Coca-Cola Classic'."
        ),
        "briefing_text": (
            "We are Coca-Cola's marketing research team. We are considering replacing our "
            "flagship Coca-Cola formula with a new, smoother and sweeter recipe. "
            "Blind taste tests with 200,000 consumers showed that 55% preferred the new "
            "formula over the existing one, and 52% preferred it over Pepsi.\n\n"
            "The new formula is slightly sweeter, with a smoother finish. We plan to "
            "rebrand it simply as 'Coca-Cola', retiring the 99-year-old original recipe. "
            "We believe this will help us compete more effectively with Pepsi in taste tests "
            "and reclaim market share among younger consumers."
        ),
        "prompt_question": "How do you feel about Coca-Cola replacing its original formula with a new, sweeter recipe?",
        "simulation_type": "concept_test",
        "ground_truth": {
            "sentiment": "Negative",
            "positive_pct": 12,
            "neutral_pct": 9,
            "negative_pct": 79,
            "top_themes": [
                "nostalgia for original formula",
                "brand identity betrayal",
                "taste preference for old formula",
                "anger at removal of a classic",
                "brand loyalty violated",
            ],
            "outcome_summary": (
                "Massive consumer backlash. Over 400,000 complaints. "
                "New Coke was withdrawn within 79 days. "
                "Internal Coca-Cola research showed 79% of consumers preferred the original formula."
            ),
            "source_notes": (
                "Backer (1987), 'The Care and Feeding of Ideas'; "
                "Pendergrast (1993), 'For God, Country and Coca-Cola'; "
                "Coca-Cola Company press archives 1985."
            ),
        },
        "source_citations": [
            "Backer, B. (1987). The Care and Feeding of Ideas. Times Books.",
            "Pendergrast, M. (1993). For God, Country and Coca-Cola. Scribner.",
            "NYT, July 11 1985: 'Coke Brings Back Its Old Formula'",
        ],
    },
    {
        "slug": "dove_real_beauty_2004",
        "title": "Dove Real Beauty Campaign (2004)",
        "category": "ad_campaign",
        "description": (
            "In 2004, Dove launched the 'Campaign for Real Beauty', featuring non-model women "
            "of varying ages, sizes, and ethnicities in their advertising. The campaign challenged "
            "conventional beauty standards. It was a significant departure from industry norms "
            "and generated extensive media coverage and consumer discussion. The campaign drove "
            "a measurable uplift in Dove sales and brand perception."
        ),
        "briefing_text": (
            "We are Dove's marketing team. We are launching a new advertising campaign called "
            "'Real Beauty'. Instead of using professional models, our ads will feature "
            "real women of different ages, sizes, shapes, and ethnicities — as they actually are, "
            "without retouching.\n\n"
            "The campaign's message is that beauty is diverse and not defined by a narrow ideal. "
            "We want to celebrate natural beauty and encourage women to feel confident in their "
            "own skin. The first execution features six 'real women' on a giant billboard in "
            "Times Square, with passersby voting via SMS on whether each woman is 'fat or fab?' "
            "and 'wrinkled or wonderful?'"
        ),
        "prompt_question": "How do you feel about Dove's new 'Real Beauty' campaign featuring real women instead of professional models?",
        "simulation_type": "concept_test",
        "ground_truth": {
            "sentiment": "Positive",
            "positive_pct": 68,
            "neutral_pct": 18,
            "negative_pct": 14,
            "top_themes": [
                "authenticity and relatability",
                "challenge to unrealistic beauty standards",
                "empowerment and self-confidence",
                "refreshingly different from typical advertising",
                "some concern over the 'fat or fab' framing",
            ],
            "outcome_summary": (
                "Broadly positive consumer reception. Dove sales increased significantly. "
                "The campaign won multiple advertising awards and generated global media coverage. "
                "Some criticism around the interactive 'fat or fab' SMS mechanic."
            ),
            "source_notes": (
                "Unilever annual reports 2004–2006; "
                "Fielding, D. et al. (2008), 'The Real Beauty of Dove', Journal of Advertising Research."
            ),
        },
        "source_citations": [
            "Fielding, D., Lewis, V., & White, L. (2008). The Real Beauty of Dove. Journal of Advertising Research.",
            "Unilever Annual Report 2005.",
        ],
    },
    {
        "slug": "tropicana_redesign_2009",
        "title": "Tropicana Packaging Redesign (2009)",
        "category": "product_launch",
        "description": (
            "In January 2009, PepsiCo replaced Tropicana's iconic orange-with-straw packaging "
            "with a minimalist design featuring a glass of orange juice. Consumer reaction was "
            "overwhelmingly negative. Sales dropped 20% in the first month — approximately "
            "$30 million in lost sales. PepsiCo reversed the decision within 6 weeks."
        ),
        "briefing_text": (
            "We are PepsiCo's brand team for Tropicana. We have redesigned the packaging for "
            "Tropicana Pure Premium orange juice. The new design replaces our well-known "
            "'orange with a straw' image with a cleaner, more modern look featuring a large "
            "glass of freshly poured orange juice.\n\n"
            "The new wordmark is rotated vertically. The cap has been redesigned to look like "
            "a sliced orange. We believe this modernises the brand and moves it away from what "
            "we see as a dated visual identity. The new packaging will roll out nationally "
            "starting January 2009."
        ),
        "prompt_question": "How do you feel about Tropicana's new packaging design replacing the iconic orange-with-straw image?",
        "simulation_type": "concept_test",
        "ground_truth": {
            "sentiment": "Negative",
            "positive_pct": 8,
            "neutral_pct": 12,
            "negative_pct": 80,
            "top_themes": [
                "loss of iconic brand recognition",
                "new design looks generic",
                "confusion at point of sale",
                "emotional attachment to original packaging",
                "modernisation feels unnecessary",
            ],
            "outcome_summary": (
                "Strongly negative reaction. Sales fell 20% in one month (~$30M loss). "
                "PepsiCo reversed the redesign within 6 weeks of launch."
            ),
            "source_notes": (
                "Stuart Elliot (2009), 'Tropicana Discovers Some Buyers Are Passionate About Packaging', NYT; "
                "PepsiCo earnings call Q1 2009."
            ),
        },
        "source_citations": [
            "Elliot, S. (2009, February 22). Tropicana Discovers Some Buyers Are Passionate About Packaging. NYT.",
            "Zmuda, N. (2009, February 23). Tropicana line's sales plunge 20% post-rebranding. Advertising Age.",
        ],
    },
    {
        "slug": "apple_iphone_2007",
        "title": "Original iPhone Announcement (2007)",
        "category": "product_launch",
        "description": (
            "On January 9, 2007, Steve Jobs announced the original iPhone at Macworld. "
            "The device combined a phone, an iPod, and an internet communicator. "
            "Early consumer and media reaction was overwhelmingly enthusiastic, particularly "
            "among early adopters and tech consumers. Pre-launch coverage generated massive "
            "anticipation. The iPhone launched in June 2007 and sold 1 million units in 74 days."
        ),
        "briefing_text": (
            "We are Apple's product team. We are announcing a revolutionary new product called "
            "the iPhone. It is a widescreen iPod with touch controls, a mobile phone, and "
            "a breakthrough internet communications device — all in one.\n\n"
            "The iPhone has no physical keyboard. The entire front face is a touchscreen. "
            "It runs a full version of OS X. It has a 2-megapixel camera, visual voicemail, "
            "and a Safari web browser. It will be priced at $499 for the 4GB model and "
            "$599 for the 8GB model with a 2-year AT&T contract. It goes on sale June 29, 2007."
        ),
        "prompt_question": "How do you react to Apple's announcement of the iPhone — a touchscreen phone with no physical keyboard?",
        "simulation_type": "concept_test",
        "ground_truth": {
            "sentiment": "Positive",
            "positive_pct": 72,
            "neutral_pct": 16,
            "negative_pct": 12,
            "top_themes": [
                "excitement about touch interface",
                "convergence of phone and iPod",
                "concern about high price",
                "curiosity about no physical keyboard",
                "anticipation of a revolutionary device",
            ],
            "outcome_summary": (
                "Overwhelmingly positive early adopter and tech-enthusiast reaction. "
                "Pre-launch media coverage was exceptional. "
                "1 million units sold in 74 days. Some concern about the $599 price point "
                "and AT&T exclusivity."
            ),
            "source_notes": (
                "Apple Q3 2007 earnings call; "
                "Mossberg, W. (2007), WSJ iPhone review; "
                "Pogue, D. (2007), NYT iPhone review."
            ),
        },
        "source_citations": [
            "Mossberg, W. (2007, June 27). Apple iPhone. The Wall Street Journal.",
            "Apple Q3 2007 Earnings Call Transcript.",
        ],
    },
    {
        "slug": "gap_logo_redesign_2010",
        "title": "Gap Logo Redesign (2010)",
        "category": "brand_perception",
        "description": (
            "In October 2010, Gap quietly replaced its 20-year-old logo — a blue box with "
            "'GAP' in white Spenser typeface — with a new design using Helvetica and a small "
            "blue gradient square. The response on social media and among consumers was "
            "immediately and almost universally negative. Gap reversed the decision within "
            "6 days and restored the original logo."
        ),
        "briefing_text": (
            "We are Gap's brand team. We have redesigned the Gap logo for the first time in "
            "20 years. The new logo uses a clean Helvetica font in black, with a small blue "
            "gradient square partially overlapping the 'p'. The design is meant to signal "
            "a modern, forward-looking Gap — 'a more contemporary, modern expression' of the brand.\n\n"
            "We are rolling out the new logo across all Gap stores, online properties, and "
            "marketing materials. The classic blue box with white GAP lettering will be retired."
        ),
        "prompt_question": "How do you feel about Gap's new logo replacing its iconic blue box design?",
        "simulation_type": "concept_test",
        "ground_truth": {
            "sentiment": "Negative",
            "positive_pct": 5,
            "neutral_pct": 8,
            "negative_pct": 87,
            "top_themes": [
                "new logo looks cheap and generic",
                "loss of iconic brand identity",
                "Helvetica feels uninspired",
                "emotional attachment to original blue box",
                "calls to revert immediately",
            ],
            "outcome_summary": (
                "Near-universal negative reaction on social media and consumer forums. "
                "The redesign became a viral example of brand failure. "
                "Gap reversed the decision after just 6 days."
            ),
            "source_notes": (
                "Nussbaum, B. (2010), 'Gap's Logo Disaster: Arrogance + Ignorance', Fast Company; "
                "Heller, S. (2010), 'Gap Logo Fail', NYT Design blog."
            ),
        },
        "source_citations": [
            "Nussbaum, B. (2010, October 6). Gap's Logo Disaster. Fast Company.",
            "Heller, S. (2010, October 8). Gap Logo. The New York Times Arts Beat.",
        ],
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        seeded = 0
        for data in CASES:
            existing = db.query(BenchmarkCase).filter_by(slug=data["slug"]).first()
            if existing:
                print(f"  skip: {data['slug']} already exists")
                continue
            case = BenchmarkCase(
                created_at=datetime.utcnow(),
                **{k: v for k, v in data.items()},
            )
            db.add(case)
            seeded += 1
            print(f"  added: {data['slug']}")
        db.commit()
        print(f"\nDone — {seeded} case(s) seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
