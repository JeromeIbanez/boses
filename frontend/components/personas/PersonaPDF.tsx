import { Document, Page, View, Text, Image, StyleSheet } from "@react-pdf/renderer";

export interface PersonaPDFData {
  full_name: string;
  age: number;
  gender: string;
  location: string;
  occupation: string;
  income_level: string;
  educational_background?: string | null;
  family_situation?: string | null;
  personality_traits?: string[] | null;
  archetype_label?: string | null;
  psychographic_segment?: string | null;
  code?: string;
  // Drives / motivations
  values_and_motivations?: string | null;
  background?: string | null;
  goals?: string | null;
  pain_points?: string | null;
  aspirational_identity?: string | null;
  buying_triggers?: string | null;
  // Brands / digital
  brand_attitudes?: string | null;
  digital_behavior?: string | null;
  media_consumption?: string | null;
  purchase_behavior?: string | null;
  spending_habits?: string | null;
  tech_savviness?: string | null;
  // Narrative
  day_in_the_life?: string | null;
  data_source_references?: string[] | null;
  // Pre-resolved avatar (base64 or null)
  avatarBase64?: string | null;
  generated_at?: string;
}

const Z = {
  900: "#18181b",
  700: "#3f3f46",
  600: "#52525b",
  500: "#71717a",
  400: "#a1a1aa",
  300: "#d4d4d8",
  200: "#e4e4e7",
  100: "#f4f4f5",
  50: "#fafafa",
};

const s = StyleSheet.create({
  page: {
    padding: 40,
    fontFamily: "Helvetica",
    backgroundColor: "#ffffff",
    fontSize: 9,
    color: Z[700],
  },
  // Header
  header: {
    flexDirection: "row",
    gap: 16,
    marginBottom: 20,
    alignItems: "flex-start",
  },
  avatar: {
    width: 84,
    height: 84,
    borderRadius: 8,
    backgroundColor: Z[900],
    objectFit: "cover",
  },
  avatarFallback: {
    width: 84,
    height: 84,
    borderRadius: 8,
    backgroundColor: Z[900],
    alignItems: "center",
    justifyContent: "center",
  },
  avatarInitial: {
    fontSize: 28,
    fontFamily: "Helvetica-Bold",
    color: "#ffffff",
  },
  identity: {
    flex: 1,
    paddingTop: 2,
  },
  fullName: {
    fontSize: 22,
    fontFamily: "Helvetica-Bold",
    color: Z[900],
    marginBottom: 4,
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 4,
    marginBottom: 5,
  },
  chip: {
    backgroundColor: Z[100],
    borderRadius: 99,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  chipText: {
    fontSize: 8,
    color: Z[600],
  },
  demographicText: {
    fontSize: 9,
    color: Z[500],
    marginBottom: 2,
  },
  codeText: {
    fontFamily: "Courier",
    fontSize: 8,
    color: Z[400],
    marginTop: 5,
  },
  // Divider
  divider: {
    height: 1,
    backgroundColor: Z[100],
    marginBottom: 16,
  },
  // At a glance
  glanceRow: {
    flexDirection: "row",
    gap: 0,
    backgroundColor: Z[50],
    borderRadius: 8,
    padding: 12,
    marginBottom: 14,
  },
  glanceItem: {
    flex: 1,
    paddingRight: 12,
  },
  glanceLabel: {
    fontSize: 7,
    color: Z[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  glanceValue: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    color: Z[700],
  },
  // Traits
  traitsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 4,
    marginBottom: 16,
  },
  traitChip: {
    backgroundColor: Z[100],
    borderRadius: 99,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  traitChipText: {
    fontSize: 8,
    color: Z[600],
  },
  // Section
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 7,
    fontFamily: "Helvetica-Bold",
    color: Z[400],
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 10,
    paddingBottom: 5,
    borderBottomWidth: 1,
    borderBottomColor: Z[100],
  },
  twoCol: {
    flexDirection: "row",
    gap: 16,
  },
  col: {
    flex: 1,
  },
  fieldLabel: {
    fontSize: 7,
    fontFamily: "Helvetica-Bold",
    color: Z[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 3,
  },
  fieldValue: {
    fontSize: 9,
    color: Z[600],
    lineHeight: 1.5,
    marginBottom: 10,
  },
  // Day in life
  dayBlock: {
    borderLeftWidth: 2,
    borderLeftColor: Z[200],
    paddingLeft: 12,
    marginBottom: 16,
  },
  dayText: {
    fontSize: 9,
    color: Z[500],
    fontFamily: "Helvetica-Oblique",
    lineHeight: 1.6,
  },
  // Sources
  sourceItem: {
    fontSize: 8,
    color: Z[400],
    marginBottom: 2,
  },
  // Footer
  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: "auto",
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: Z[100],
  },
  footerText: {
    fontSize: 8,
    color: Z[300],
  },
});

function Field({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <View>
      <Text style={s.fieldLabel}>{label}</Text>
      <Text style={s.fieldValue}>{value}</Text>
    </View>
  );
}

function PersonaPage({ p }: { p: PersonaPDFData }) {
  const motivations = p.values_and_motivations ?? p.background;
  const secondaryMotivation = p.goals ?? p.aspirational_identity;

  return (
    <Page size="A4" style={s.page}>
      {/* Header */}
      <View style={s.header}>
        {p.avatarBase64 ? (
          <Image src={p.avatarBase64} style={s.avatar} />
        ) : (
          <View style={s.avatarFallback}>
            <Text style={s.avatarInitial}>{p.full_name.charAt(0)}</Text>
          </View>
        )}
        <View style={s.identity}>
          <Text style={s.fullName}>{p.full_name}</Text>
          {(p.archetype_label || p.psychographic_segment) && (
            <View style={s.chipRow}>
              {p.archetype_label && (
                <View style={s.chip}>
                  <Text style={s.chipText}>{p.archetype_label}</Text>
                </View>
              )}
              {p.psychographic_segment && (
                <View style={s.chip}>
                  <Text style={s.chipText}>{p.psychographic_segment}</Text>
                </View>
              )}
            </View>
          )}
          <Text style={s.demographicText}>
            {p.age} · {p.gender} · {p.location}
          </Text>
          <Text style={s.demographicText}>{p.occupation}</Text>
          {p.code && <Text style={s.codeText}>#{p.code}</Text>}
        </View>
      </View>

      <View style={s.divider} />

      {/* At a glance */}
      <View style={s.glanceRow}>
        <View style={s.glanceItem}>
          <Text style={s.glanceLabel}>Income</Text>
          <Text style={s.glanceValue}>{p.income_level}</Text>
        </View>
        {p.educational_background && (
          <View style={s.glanceItem}>
            <Text style={s.glanceLabel}>Education</Text>
            <Text style={s.glanceValue}>{p.educational_background}</Text>
          </View>
        )}
        {p.family_situation && (
          <View style={s.glanceItem}>
            <Text style={s.glanceLabel}>Family</Text>
            <Text style={s.glanceValue}>{p.family_situation}</Text>
          </View>
        )}
      </View>

      {/* Personality traits */}
      {p.personality_traits && p.personality_traits.length > 0 && (
        <View style={s.traitsRow}>
          {p.personality_traits.map((t) => (
            <View key={t} style={s.traitChip}>
              <Text style={s.traitChipText}>{t}</Text>
            </View>
          ))}
        </View>
      )}

      {/* What Drives Them */}
      {(motivations || secondaryMotivation || p.pain_points || p.buying_triggers) && (
        <View style={s.section}>
          <Text style={s.sectionTitle}>What Drives Them</Text>
          <View style={s.twoCol}>
            <View style={s.col}>
              <Field label="Values & Motivations" value={motivations} />
              <Field label="Pain Points" value={p.pain_points} />
            </View>
            <View style={s.col}>
              <Field label={p.goals ? "Goals" : "Aspirational Identity"} value={secondaryMotivation} />
              <Field label="Buying Triggers" value={p.buying_triggers} />
            </View>
          </View>
        </View>
      )}

      {/* Brands & Digital Life */}
      {(p.brand_attitudes || p.digital_behavior || p.media_consumption || p.purchase_behavior || p.spending_habits || p.tech_savviness) && (
        <View style={s.section}>
          <Text style={s.sectionTitle}>Brands & Digital Life</Text>
          <View style={s.twoCol}>
            <View style={s.col}>
              <Field label="Brand Attitudes" value={p.brand_attitudes} />
              <Field label="Media Consumption" value={p.media_consumption} />
              <Field label="Tech Savviness" value={p.tech_savviness} />
            </View>
            <View style={s.col}>
              <Field label="Digital Behavior" value={p.digital_behavior} />
              <Field label={p.spending_habits ? "Spending Habits" : "Purchase Behavior"} value={p.spending_habits ?? p.purchase_behavior} />
            </View>
          </View>
        </View>
      )}

      {/* A Day in Their Life */}
      {p.day_in_the_life && (
        <View style={s.section}>
          <Text style={s.sectionTitle}>A Day in Their Life</Text>
          <View style={s.dayBlock}>
            <Text style={s.dayText}>"{p.day_in_the_life}"</Text>
          </View>
        </View>
      )}

      {/* Grounding Sources */}
      {p.data_source_references && p.data_source_references.length > 0 && (
        <View style={s.section}>
          <Text style={s.sectionTitle}>Grounding Sources</Text>
          {p.data_source_references.map((ref) => (
            <Text key={ref} style={s.sourceItem}>· {ref}</Text>
          ))}
        </View>
      )}

      {/* Footer */}
      <View style={s.footer}>
        <Text style={s.footerText}>Generated by Boses</Text>
        <Text style={s.footerText}>
          {p.generated_at
            ? new Date(p.generated_at).toLocaleDateString()
            : new Date().toLocaleDateString()}
        </Text>
      </View>
    </Page>
  );
}

export default function PersonasPDF({ personas }: { personas: PersonaPDFData[] }) {
  return (
    <Document>
      {personas.map((p, i) => (
        <PersonaPage key={p.code ?? p.full_name + i} p={p} />
      ))}
    </Document>
  );
}
