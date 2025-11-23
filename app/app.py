import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.repository import EvalRun, EvalRunRepository

BOOTSTRAPING_AGG_FUNC = np.mean

st.set_page_config(
    page_title="AI Actions Evaluation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-rate {
        font-size: 1.5rem;
        font-weight: 600;
    }
    .run-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_repository(db_path: str = "eval_runs.db"):
    """Get repository instance (cached)."""
    return EvalRunRepository(db_path)


@st.cache_data
def get_cached_summary_stats(db_path: str):
    """Get summary stats (cached)."""
    repo = get_repository(db_path)
    return repo.get_summary_stats()


@st.cache_data
def get_cached_all_runs(db_path: str, limit: int = 1000):
    """Get all runs for filters (cached)."""
    repo = get_repository(db_path)
    return repo.get_eval_runs(limit=limit)


@st.cache_data
def get_cached_filtered_runs(db_path: str, model_parent, model_name, scenario_type, limit: int, order_by: str, order_desc: bool):
    """Get filtered runs (cached)."""
    repo = get_repository(db_path)
    return repo.get_eval_runs(
        model_parent=model_parent,
        model_name=model_name,
        scenario_type=scenario_type,
        limit=limit,
        order_by=order_by,
        order_desc=order_desc
    )


@st.cache_data
def get_cached_eval_run(db_path: str, run_id: int):
    """Get single eval run (cached)."""
    repo = get_repository(db_path)
    return repo.get_eval_run(run_id)


@st.cache_data
def process_models_summary_data(db_path: str, limit: int = 1000):
    """Process models summary data (cached)."""
    all_runs = get_cached_all_runs(db_path, limit)
    if not all_runs:
        return []
    
    model_data = {}
    for run in all_runs:
        if run.model_name not in model_data:
            model_data[run.model_name] = {
                'model_parent': run.model_parent,
                'success_rates': []
            }
        
        if run.summary:
            success_rate = run.summary.get('success_rate', None)
            if success_rate is not None:
                model_data[run.model_name]['success_rates'].append(success_rate)
    
    models_summary_data = []
    for model_name, data in model_data.items():
        aggregated_success_rate = None
        if data['success_rates']:
            aggregated_success_rate = BOOTSTRAPING_AGG_FUNC(data['success_rates'])
        
        models_summary_data.append({
            'Model Name': model_name,
            'Parent Name': data['model_parent'] if data['model_parent'] else 'N/A',
            'Success Rate': f"{aggregated_success_rate:.1%}" if aggregated_success_rate is not None else "N/A"
        })
    
    return models_summary_data


@st.cache_data
def process_runs_dataframe(db_path: str, model_parent, model_name, scenario_type, limit: int, order_by: str, order_desc: bool):
    """Process runs into dataframe (cached)."""
    runs = get_cached_filtered_runs(db_path, model_parent, model_name, scenario_type, limit, order_by, order_desc)
    if not runs:
        return None
    
    runs_data = []
    for run in runs:
        runs_data.append(run.model_dump(exclude=["max_tokens", "results"]))
    
    return pd.DataFrame(runs_data)


@st.cache_data
def process_results_dataframe(db_path: str, run_id: int):
    """Process results into dataframe (cached)."""
    run = get_cached_eval_run(db_path, run_id)
    if not run or not run.results:
        return None
    
    results_df = pd.DataFrame(run.results)
    results_df['messages'] = results_df['messages'].apply(lambda msgs: [f"{m['role']}: {m['content']}" for m in msgs])
    results_df['tools'] = results_df['tools'].apply(lambda tools: [tool['function']['name'] for tool in tools])
    
    return results_df


def format_datetime(dt_str: str) -> str:
    """Format datetime string for display."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str


def main():
    st.markdown('<h1 class="main-header">📊 Evaluation Runs Dashboard</h1>', unsafe_allow_html=True)
    
    db_path = st.sidebar.text_input("Database Path", value="eval_runs.db")
    
    try:
        stats = get_cached_summary_stats(db_path)
    except Exception as e:
        st.error(f"Error loading database: {e}")
        st.stop()
    
    st.sidebar.header("🔍 Filters Run List")
    
    all_runs: list[EvalRun] | None = get_cached_all_runs(db_path, limit=1000)
    unique_models = sorted(set(run.model_name for run in all_runs)) if all_runs else []
    unique_scenarios = sorted(set(run.scenario_type for run in all_runs)) if all_runs else []
    unique_model_parents = sorted(set(run.model_parent for run in all_runs)) if all_runs else []
    
    selected_model_parent = st.sidebar.selectbox(
        "Model Parent",
        options=[None] + unique_model_parents,
        format_func=lambda x: "All Model Parents" if x is None else x
    )

    selected_model = st.sidebar.selectbox(
        "Model Name",
        options=[None] + unique_models,
        format_func=lambda x: "All Models" if x is None else x
    )
    
    selected_scenario = st.sidebar.selectbox(
        "Scenario Type",
        options=[None] + unique_scenarios,
        format_func=lambda x: "All Scenarios" if x is None else x
    )
    
    limit = st.sidebar.number_input("Max Results", min_value=1, max_value=1000, value=1)
    
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "📋 Runs List", "🔍 Run Details"])
    
    with tab1:
        st.header("Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Runs", stats['total_runs'])
        
        with col2:
            num_models = len(stats['by_model'])
            st.metric("Unique Models", num_models)
        
        with col3:
            num_scenarios = len(stats['by_scenario_type'])
            st.metric("Scenario Types", num_scenarios)
        
        with col4:
            if stats['latest_run']:
                latest_date = format_datetime(stats['latest_run']['created_at'])
                st.metric("Latest Run", latest_date.split()[0])
            else:
                st.metric("Latest Run", "N/A")
        
        st.subheader("Models Summary")
        models_summary_data = process_models_summary_data(db_path, limit=1000)
        
        if models_summary_data:
            models_summary_df = pd.DataFrame(models_summary_data)
            st.dataframe(
                models_summary_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No model data available for summary table.")
        
        if stats['latest_run']:
            st.subheader("Latest Run")
            latest = stats['latest_run']
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**ID:** {latest['id']}")
            with col2:
                st.write(f"**Model:** {latest['model_name']}")
            with col3:
                st.write(f"**Scenario:** {latest['scenario_type']}")
    
    with tab2:
        st.header("Evaluation Runs")
        
        df = process_runs_dataframe(
            db_path,
            selected_model_parent,
            selected_model,
            selected_scenario,
            limit,
            "created_at",
            True
        )
        
        if df is None or df.empty:
            st.info("No evaluation runs found matching the filters.")
        else:
            st.write(f"Showing {len(df)} run(s)")
            
            # Display table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )
            
            #st.subheader("View Run Details")
            #run_ids = [run.id for run in runs]
            #selected_run_id = st.selectbox(
            #    "Select a run to view details",
            #    options=run_ids,
            #    format_func=lambda x: f"Run #{x}"
            #)
            #
            #if selected_run_id:
            #    st.session_state['selected_run_id'] = selected_run_id
    
    with tab3:
        st.header("Run Details")
        
        run_id_input = st.number_input(
            "Enter Run ID",
            min_value=1,
            value=st.session_state.get('selected_run_id', 1),
            key="run_id_input"
        )
        
        if st.button("Load Run Details") or 'selected_run_id' in st.session_state:
            run_id = st.session_state.get('selected_run_id', run_id_input)
            
            run = get_cached_eval_run(db_path, run_id)
            
            if not run:
                st.error(f"Run #{run_id} not found.")
            else:
                st.subheader("Run Information")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Run ID:** {run.id}")
                    st.write(f"**Model:** {run.model_name}")
                    st.write(f"**Scenario Type:** {run.scenario_type}")
                
                with col2:
                    st.write(f"**Created:** {format_datetime(run.created_at)}")
                    if run.temperature is not None:
                        st.write(f"**Temperature:** {run.temperature}")
                    if run.top_p is not None:
                        st.write(f"**Top-p:** {run.top_p}")
                
                with col3:
                    #if run.max_tokens is not None:
                    #    st.write(f"**Max Tokens:** {run.max_tokens}")
                    st.write(f"**Total Scenarios:** {len(run.results)}")
                
                if run.summary:
                    st.subheader("Summary Statistics")
                    summary = run.summary
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        total_scenarios = summary.get('total_scenarios', len(run.results))
                        st.metric("Total Scenarios", total_scenarios)
                    
                    with col2:
                        passed = [v.get('passed', 0) for k, v in summary.items() if isinstance(v, dict)]
                        st.metric("Passed", BOOTSTRAPING_AGG_FUNC(passed))
                    
                    with col3:
                        failed = [total_scenarios - v.get('passed', 0) for k, v in summary.items() if isinstance(v, dict)]
                        st.metric("Failed", BOOTSTRAPING_AGG_FUNC(failed))
                    
                    with col4:
                        success_rates = [v.get('success_rate', 0) for k, v in summary.items() if isinstance(v, dict)]
                        success_rate = BOOTSTRAPING_AGG_FUNC(success_rates)
                        st.metric("Success Rate", f"{success_rate:.1%}")
                
                st.subheader("Results")
                
                if run.results:
                    results_df = process_results_dataframe(db_path, run_id)
                    
                    if results_df is not None:
                        st.dataframe(
                            results_df,
                            use_container_width=True,
                            hide_index=True,
                        )
                    
                    #with st.expander("View Detailed Results (First 5)"):
                    #    for i, result in enumerate(run.results[:5], 1):
                    #        st.write(f"**Scenario {i}:**")
                    #        st.json(result)
                    #        st.divider()
                else:
                    st.info("No results available for this run.")


if __name__ == "__main__":
    main()

