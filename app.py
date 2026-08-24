import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="SKU Sequencing Optimizer",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 SKU Production Sequence Optimizer")

st.markdown("""
Upload:

1. Cost Matrix CSV
2. Monthly SKU CSV

The tool will generate the optimized production sequence using:
- Cost Matrix minimization
- Attribute based tie breaking
""")

# --------------------------
# Upload Files
# --------------------------

cost_file = st.file_uploader(
    "Upload Cost Matrix CSV",
    type=["csv"]
)

sku_file = st.file_uploader(
    "Upload Monthly SKU CSV",
    type=["csv"]
)

if cost_file and sku_file:

    try:

        # --------------------------
        # Load Data
        # --------------------------

        cost_df = pd.read_csv(cost_file, index_col=0)
        sku_df = pd.read_csv(sku_file)

        # --------------------------
        # Clean Data
        # --------------------------

        sku_df.columns = sku_df.columns.str.strip().str.upper()

        cost_df.index = cost_df.index.astype(str).str.strip()
        cost_df.columns = cost_df.columns.astype(str).str.strip()

        # --------------------------
        # Detect Product Code Column
        # --------------------------

        prod_cols = [
            c for c in sku_df.columns
            if "PRODUCT" in c and "CODE" in c
        ]

        if len(prod_cols) == 0:
            st.error("Product Code column not found.")
            st.stop()

        sap_col = prod_cols[0]

        priority_cols = [
            "BODY",
            "GP CODE",
            "THICKNESS",
            "BELT",
            "BELT TYPE",
            "SURFACE CATEGORY",
            "PRODUCT SIZE",
            "COLLECTION"
        ]

        for col in priority_cols:
            if col not in sku_df.columns:
                sku_df[col] = ""

        sku_df[sap_col] = sku_df[sap_col].astype(str).str.strip()

        # --------------------------
        # Common SKUs
        # --------------------------

        common_skus = list(
            set(sku_df[sap_col]).intersection(cost_df.index)
        )

        if len(common_skus) < 2:
            st.error("Less than 2 common SKUs found.")
            st.stop()

        sku_df = sku_df[
            sku_df[sap_col].isin(common_skus)
        ].reset_index(drop=True)

        cost_df = cost_df.loc[
            common_skus,
            common_skus
        ]

        st.success(f"{len(common_skus)} Common SKUs Found")

        # --------------------------
        # Priority Function
        # --------------------------

        def priority_score(base, candidate):

            score = 0

            for col in priority_cols:

                if (
                    str(base[col]).strip() != ""
                    and base[col] == candidate[col]
                ):
                    score += 1

            return score

        # --------------------------
        # Optimization
        # --------------------------

        progress = st.progress(0)

        remaining = sku_df.copy()
        sequence = []

        current = remaining.iloc[0]

        sequence.append(current)

        remaining = remaining.iloc[1:].reset_index(drop=True)

        total_rows = len(sku_df)

        while not remaining.empty:

            current_sku = current[sap_col]

            costs = cost_df.loc[
                current_sku,
                remaining[sap_col]
            ].astype(float)

            min_cost = costs.min()

            min_skus = costs[
                costs == min_cost
            ].index.tolist()

            tied = remaining[
                remaining[sap_col].isin(min_skus)
            ].copy()

            if len(tied) > 1:

                tied["priority"] = tied.apply(
                    lambda r: priority_score(current, r),
                    axis=1
                )

                next_row = tied.sort_values(
                    "priority",
                    ascending=False
                ).iloc[0]

            else:
                next_row = tied.iloc[0]

            sequence.append(next_row)

            remaining = remaining[
                remaining[sap_col] != next_row[sap_col]
            ].reset_index(drop=True)

            current = next_row

            progress.progress(
                len(sequence) / total_rows
            )

        # --------------------------
        # Output
        # --------------------------

        final_df = pd.DataFrame(sequence)

        final_df.insert(
            0,
            "Sequence_No",
            range(1, len(final_df) + 1)
        )

        st.success("Optimization Completed")

        st.dataframe(
            final_df,
            use_container_width=True
        )

        csv = final_df.to_csv(
            index=False
        ).encode('utf-8')

        st.download_button(
            label="📥 Download Optimized Sequence",
            data=csv,
            file_name="FINAL_OPTIMIZED_SEQUENCE.csv",
            mime="text/csv"
        )

    except Exception as e:

        st.error(str(e))
