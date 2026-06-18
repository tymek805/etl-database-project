import streamlit as st
import pandas as pd
import tempfile
import os

# Import your existing ETL logic
import etl_products
import etl_customers
import etl_inventory

# --- Page Configuration ---
st.set_page_config(
    page_title="ETL Data Importer",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚀 ETL Data Importer Dashboard")
st.markdown("Modern interface for processing Product and Customer data feeds into PostgreSQL.")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")

    scenario = st.selectbox(
        "Select ETL Scenario",
        ["Products Import", "Customers Import", "Inventory Update"]
    )

    st.divider()

    dry_run = st.checkbox("Dry Run (Validate only, no DB save)", value=True)

    file_types = ["xlsx"] if scenario == "Inventory Update" else ["csv", "json"]
    file_types_label = ", ".join(f".{file_type}" for file_type in file_types)

    uploaded_file = st.file_uploader(
        f"Upload Data Feed ({file_types_label})",
        type=file_types
    )


# --- Entity Relationship Visualizations ---
def render_schema_graph(scenario_type):
    st.subheader("🗄️ Target Database Schema")

    if scenario_type == "Products Import":
        graph_code = """
        digraph ProductsSchema {
            rankdir=LR;
            node [shape=record, style=filled, fillcolor="#f0f2f6", fontname="Helvetica"];
            edge [fontname="Helvetica", fontsize=10, color="#7d8597"];

            Kategoria [label="{Kategoria | kategoriaid (PK)\\nnazwa}"];
            Producent [label="{Producent | producentid (PK)\\nnazwa\\nkraj}"];
            Produkt [label="{Produkt | produktid (PK)\\nnazwa\\ncena\\nstanmagazynowy\\nkategoriaid (FK)\\nproducentid (FK)}", fillcolor="#e0e5ec"];

            Kategoria -> Produkt [label=" 1 : N", dir=forward];
            Producent -> Produkt [label=" 1 : N", dir=forward];
        }
        """
        st.graphviz_chart(graph_code)
        st.caption("The Products ETL process splits the flat feed into Kategoria, Producent, and Produkt tables.")

    elif scenario_type == "Inventory Update":
        graph_code = """
        digraph InventorySchema {
            rankdir=LR;
            node [shape=record, style=filled, fillcolor="#f0f2f6", fontname="Helvetica"];
            edge [fontname="Helvetica", fontsize=10, color="#7d8597"];

            Producent [label="{Producent | producentid (PK)\\nnazwa\\nkraj}"];
            Produkt [label="{Produkt | produktid (PK)\\nnazwa\\ncena\\nstanmagazynowy\\nproducentid (FK)}", fillcolor="#e0e5ec"];
            Korekta [label="{Excel Feed | nazwa\\nproducent\\nzmiana_stanu\\npowod}", fillcolor="#fff4d6"];

            Producent -> Produkt [label=" 1 : N", dir=forward];
            Korekta -> Produkt [label=" update stock", style=dashed];
        }
        """
        st.graphviz_chart(graph_code)
        st.caption("The Inventory ETL process validates stock changes and updates Produkt.stanmagazynowy.")

    elif scenario_type == "Customers Import":
        graph_code = """
        digraph CustomersSchema {
            rankdir=LR;
            node [shape=record, style=filled, fillcolor="#f0f2f6", fontname="Helvetica"];
            edge [fontname="Helvetica", fontsize=10, color="#7d8597"];

            AdrKlienta [label="{AdrKlienta | adrklientaid (PK)\\nmiejscowosck\\nulica\\nkodpocztowyk\\nkrajk}"];
            Klient [label="{Klient | klientid (PK)\\nimie\\nnazwisko\\nemail\\ntelefon\\nadrklientid (FK)}", fillcolor="#e0e5ec"];

            AdrKlienta -> Klient [label=" 1 : N", dir=forward];
        }
        """
        st.graphviz_chart(graph_code)
        st.caption(
            "The Customers ETL process normalizes addresses into the AdrKlienta table and links them to the Klient table.")


# --- Main Workspace ---
if uploaded_file:
    ext = os.path.splitext(uploaded_file.name)[1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🔍 Initial Data Preview")
        try:
            if ext == ".csv":
                df = pd.read_csv(tmp_path)
            elif ext == ".json":
                df = pd.read_json(tmp_path)
            elif ext == ".xlsx":
                df = pd.read_excel(tmp_path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
            st.dataframe(df.head(15), width="stretch")
            st.caption(f"Showing up to the first 15 rows of {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error generating data preview: {e}")

    with col2:
        render_schema_graph(scenario)

    st.divider()

    # 2. Execution Trigger
    if st.button("▶️ Run ETL Process", type="primary", width="stretch"):
        with st.spinner("Executing pipeline and synchronizing with database..."):
            try:
                # --- PRODUCTS SCENARIO ---
                if scenario == "Products Import":
                    rejects_path = f"{tmp_path}_rejects.csv"
                    result = etl_products.run_etl(
                        file_path=tmp_path,
                        dry_run=dry_run,
                        rejects_file=rejects_path
                    )

                    st.subheader("📊 Execution Statistics")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Rows Extracted", result.extracted)
                    c2.metric("Products Transformed", result.transformed)
                    c3.metric("Loaded to DB", result.loaded if not dry_run else "Skipped (Dry Run)")
                    c4.metric("Errors / Rejected", result.skipped,
                              delta_color="inverse" if result.skipped > 0 else "normal")

                    st.info(f"💰 **Total Inventory Value Processed:** {result.total_inventory_value:,} PLN")

                    st.write("### Database Entity Updates")
                    col_d1, col_d2 = st.columns(2)
                    col_d1.write(f"🟢 **Inserted Products:** {result.inserted}")
                    col_d1.write(f"🔄 **Updated Products:** {result.updated}")
                    col_d2.write(f"📁 **Categories Created:** {result.categories_created}")
                    col_d2.write(f"🏭 **Producers Created:** {result.producers_created}")

                    if result.skipped > 0 and result.rejected_file and os.path.exists(result.rejected_file):
                        st.error(f"⚠️ {result.skipped} rows were rejected due to validation errors.")
                        rejects_df = pd.read_csv(result.rejected_file)
                        st.dataframe(rejects_df, width="stretch")

                        with open(result.rejected_file, "rb") as f:
                            st.download_button(
                                label="⬇️ Download Rejects Report (.csv)",
                                data=f,
                                file_name="products_rejected.csv",
                                mime="text/csv"
                        )

                # --- INVENTORY SCENARIO ---
                elif scenario == "Inventory Update":
                    rejects_path = f"{tmp_path}_rejects.csv"
                    result = etl_inventory.run_etl(
                        file_path=tmp_path,
                        dry_run=dry_run,
                        rejects_file=rejects_path
                    )

                    st.subheader("Execution Statistics")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Rows Extracted", result.extracted)
                    c2.metric("Valid Updates", result.validated)
                    c3.metric("Loaded to DB", result.loaded if not dry_run else "Skipped (Dry Run)")
                    c4.metric("Rejected", result.skipped,
                              delta_color="inverse" if result.skipped > 0 else "normal")

                    st.info(f"**Total Valid Stock Delta:** {result.total_stock_delta}")

                    st.write("### Database Entity Updates")
                    if dry_run:
                        st.write(f"**Products that would be updated:** {result.validated}")
                    else:
                        st.write(f"**Updated Products:** {result.updated}")

                    if result.skipped > 0 and result.rejected_file and os.path.exists(result.rejected_file):
                        st.error(f"{result.skipped} rows were rejected due to validation errors.")
                        rejects_df = pd.read_csv(result.rejected_file)
                        st.dataframe(rejects_df, width="stretch")

                        with open(result.rejected_file, "rb") as f:
                            st.download_button(
                                label="Download Rejects Report (.csv)",
                                data=f,
                                file_name="inventory_updates_rejected.csv",
                                mime="text/csv"
                            )

                # --- CUSTOMERS SCENARIO ---
                elif scenario == "Customers Import":
                    result = etl_customers.run_etl(
                        file_path=tmp_path,
                        dry_run=dry_run
                    )

                    st.subheader("📊 Execution Statistics")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Rows Extracted", result.extracted)
                    c2.metric("Customers Transformed", result.transformed)
                    c3.metric("Loaded to DB", result.loaded if not dry_run else "Skipped (Dry Run)")
                    c4.metric("Skipped", result.skipped, delta_color="inverse" if result.skipped > 0 else "normal")

                    st.write("### Database Entity Updates")
                    st.write(f"🟢 **Inserted Customers:** {result.inserted}")
                    st.write(f"🔄 **Updated Customers:** {result.updated}")

                # --- SUCCESS / WARNING BANNERS ---
                if dry_run:
                    st.warning(
                        "ℹ️ **Dry Run completed.** Data was validated but no changes were committed to the database.")
                else:
                    st.success("✅ **ETL Process completed successfully!** Database synchronization is complete.")

            except Exception as e:
                st.error(f"🚨 A critical error occurred during execution:\n\n{str(e)}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

else:
    st.info("👈 Please select a scenario and upload a data feed file from the sidebar to begin.")
