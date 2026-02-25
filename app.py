import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Elix'SIR — Simulateur", page_icon="🍸", layout="centered")

EXCEL_PATH = "liste simulateur.xlsx"
SHEET_NAME = "Liste Achats détaillée"

# -----------------------------
# Data loading
# -----------------------------
@st.cache_data
def load_data(path: str, sheet: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet)

    # Normalisation minimale des noms attendus
    expected = {
        "Catégorie": "Categorie",
        "Produit": "Produit",
        "Unité (qualif)": "Unite_qualif",
        "Unité": "Unite_ref",
        "Apport Protéine": "Proteine_ref",
        "Prix Marché": "Prix_ref",
    }
    # Tolérance: si les colonnes ont déjà ces noms exacts, on garde
    rename_map = {}
    for col in df.columns:
        if col in expected:
            rename_map[col] = expected[col]
    df = df.rename(columns=rename_map)

    # Vérifications colonnes indispensables
    required_cols = ["Categorie", "Produit", "Unite_qualif", "Unite_ref", "Proteine_ref", "Prix_ref"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            "Colonnes manquantes dans l'Excel: "
            + ", ".join(missing)
            + "\nColonnes trouvées: "
            + ", ".join(map(str, df.columns))
        )

    # Nettoyage / types
    df["Categorie"] = df["Categorie"].astype(str).str.strip()
    df["Produit"] = df["Produit"].astype(str).str.strip()
    df["Unite_qualif"] = df["Unite_qualif"].astype(str).str.strip()

    for c in ["Unite_ref", "Proteine_ref", "Prix_ref"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["Produit"]).copy()
    return df


def safe_round(x: float, ndigits: int = 2) -> float:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return 0.0
    return round(float(x), ndigits)


def compute_totals(q: float, unite_ref: float, prix_ref: float, prot_ref: float) -> tuple[float, float, float]:
    """
    q: quantité saisie (dans la même unité de référence que unite_ref)
    unite_ref: colonne D
    prix_ref: colonne F (pour unite_ref)
    prot_ref: colonne E (pour unite_ref)
    """
    if unite_ref is None or unite_ref == 0 or math.isnan(unite_ref):
        return 0.0, 0.0, 0.0

    m = q / unite_ref
    prix_total = m * prix_ref if prix_ref is not None and not math.isnan(prix_ref) else 0.0
    prot_total = m * prot_ref if prot_ref is not None and not math.isnan(prot_ref) else 0.0
    return m, prix_total, prot_total


# -----------------------------
# UI
# -----------------------------
st.title("🍸 Elix'SIR — Simulateur d’ingrédients")
st.caption("Choisis un ingrédient, sa quantité, et le simulateur calcule prix marché + apport protéine. (Référence = colonne D)")

try:
    df = load_data(EXCEL_PATH, SHEET_NAME)
except Exception as e:
    st.error("Impossible de charger les données Excel.")
    st.exception(e)
    st.stop()

# Session state panier
if "cart" not in st.session_state:
    st.session_state.cart = []  # list of dicts

# Sidebar = mode “game”
with st.sidebar:
    st.subheader("🎮 Mode jeu")
    budget = st.number_input("Budget (optionnel)", min_value=0.0, value=0.0, step=10.0, help="Si > 0, on te montre si tu dépasses.")
    protein_target = st.number_input("Objectif protéines (optionnel)", min_value=0.0, value=0.0, step=5.0, help="Si > 0, on te montre si tu atteins.")
    st.divider()
    st.write("💡 Astuce: l’unité de saisie doit correspondre à la référence (colonne D).")

# Sélection catégorie (optionnelle)
categories = ["(Toutes)"] + sorted(df["Categorie"].dropna().unique().tolist())
cat = st.selectbox("1) Catégorie", categories, index=0)

df_filtered = df.copy()
if cat != "(Toutes)":
    df_filtered = df_filtered[df_filtered["Categorie"] == cat]

# Sélection produit
products = sorted(df_filtered["Produit"].dropna().unique().tolist())
if not products:
    st.warning("Aucun produit trouvé pour cette catégorie.")
    st.stop()

prod = st.selectbox("2) Ingrédient (Produit)", products)

row = df_filtered[df_filtered["Produit"] == prod].iloc[0]
unite_qualif = row["Unite_qualif"]
unite_ref = row["Unite_ref"]
prot_ref = row["Proteine_ref"]
prix_ref = row["Prix_ref"]

st.info(f"📌 Unité (qualif) : **{unite_qualif}** | Référence (col. D) : **{unite_ref}**")

q = st.number_input("3) Quantité", min_value=0.0, value=0.0, step=1.0)

colA, colB = st.columns(2)
with colA:
    do_calc = st.button("Calculer", use_container_width=True)
with colB:
    add_cart = st.button("Ajouter au panier", use_container_width=True)

# Calcul (auto si bouton ou si on ajoute)
if do_calc or add_cart:
    if prod is None or str(prod).strip() == "":
        st.error("Veuillez sélectionner un produit.")
    elif q <= 0:
        st.error("La quantité doit être > 0.")
    elif unite_ref is None or (isinstance(unite_ref, float) and math.isnan(unite_ref)) or unite_ref == 0:
        st.error("Unité de référence (colonne D) invalide (0 ou vide).")
    else:
        m, prix_total, prot_total = compute_totals(q, float(unite_ref), float(prix_ref) if not math.isnan(prix_ref) else 0.0,
                                                  float(prot_ref) if not math.isnan(prot_ref) else 0.0)

        prix_total_r = safe_round(prix_total, 2)
        prot_total_r = safe_round(prot_total, 2)
        m_r = safe_round(m, 4)

        st.success("✅ Résultat du calcul")
        st.write(f"- Multiplicateur m = q / unité_ref = **{m_r}**")
        st.write(f"- 💰 Prix marché total = **{prix_total_r}**")
        st.write(f"- 🥩 Apport protéine total = **{prot_total_r}**")

        # Feedback “game”
        if budget and budget > 0:
            if prix_total_r > budget:
                st.warning(f"⚠️ Tu dépasses ton budget de {safe_round(prix_total_r - budget, 2)}.")
            else:
                st.info(f"👍 Budget OK. Il te reste {safe_round(budget - prix_total_r, 2)}.")
        if protein_target and protein_target > 0:
            if prot_total_r >= protein_target:
                st.balloons()
                st.info("🏆 Objectif protéines atteint !")
            else:
                st.info(f"📈 Il te manque {safe_round(protein_target - prot_total_r, 2)} pour atteindre l’objectif.")

        if add_cart:
            st.session_state.cart.append({
                "Categorie": row["Categorie"],
                "Produit": prod,
                "Unite_qualif": unite_qualif,
                "Quantite": q,
                "Unite_ref": float(unite_ref),
                "Prix_total": prix_total_r,
                "Proteine_total": prot_total_r
            })
            st.toast("Ajouté au panier ✅", icon="🧺")

st.divider()
st.subheader("🧺 Panier")

if not st.session_state.cart:
    st.write("Panier vide pour l’instant.")
else:
    cart_df = pd.DataFrame(st.session_state.cart)
    st.dataframe(cart_df, use_container_width=True, hide_index=True)

    total_price = safe_round(cart_df["Prix_total"].sum(), 2)
    total_prot = safe_round(cart_df["Proteine_total"].sum(), 2)

    st.write(f"**Total prix** : {total_price}")
    st.write(f"**Total protéines** : {total_prot}")

    if budget and budget > 0:
        if total_price > budget:
            st.error(f"💸 Budget dépassé de {safe_round(total_price - budget, 2)}")
        else:
            st.success(f"✅ Budget OK — reste {safe_round(budget - total_price, 2)}")

    if protein_target and protein_target > 0:
        if total_prot >= protein_target:
            st.success("🏆 Objectif protéines atteint (panier) !")
        else:
            st.info(f"📈 Il manque {safe_round(protein_target - total_prot, 2)} (panier)")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Vider le panier", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
    with col2:
        # export CSV
        csv = cart_df.to_csv(index=False).encode("utf-8")
        st.download_button("Télécharger panier (CSV)", data=csv, file_name="panier_game_cocktail.csv", mime="text/csv", use_container_width=True)