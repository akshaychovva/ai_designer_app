import streamlit as st
import sys
import os
import importlib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import backend.chat_engine
importlib.reload(backend.chat_engine)
from backend.chat_engine import process_architect_chat, process_component_chat, process_builder_chat, process_explain_fields, generate_terraform

st.set_page_config(layout="wide")

def get_sug_items(sug_fields):
    if isinstance(sug_fields, dict):
        return sug_fields.items()
    elif isinstance(sug_fields, list):
        return [(str(x), "") for x in sug_fields]
    else:
        return [(str(sug_fields), "")]

if "infra" not in st.session_state:
    st.session_state.infra = {}

if "show_terraform" not in st.session_state:
    st.session_state.show_terraform = False

if "architect_chat" not in st.session_state:
    st.session_state.architect_chat = []

if "builder_chat" not in st.session_state:
    st.session_state.builder_chat = []

infra = st.session_state.infra

col1, col2, col3 = st.columns([1.5, 2, 1.5])

# ------------- LEFT PANEL -------------
with col1:
    st.title("👨‍💻 Cloud Architect")
    st.write("I am your expert guide. Ask me to review your infra anytime!")

    for msg in st.session_state.architect_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask for an architect review..."):
        st.session_state.architect_chat.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.spinner("Architect is thinking..."):
            response = process_architect_chat(user_input, infra)
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.architect_chat.append({"role": "assistant", "content": response})

# ------------- MIDDLE PANEL (GENERIC) -------------
with col2:
    # Inject custom CSS for the primary button to make it green
    st.markdown("""
        <style>
        button[kind="primary"]:not([disabled]) {
            background-color: #28a745 !important;
            border-color: #28a745 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    st.title("⚙️ Interactive Builder")
    st.subheader("What do you want to deploy?")
    
    st.caption("Please provide at least 5 prompts for clear context.")

    user_msg_count = sum(1 for m in st.session_state.builder_chat if m.get("role") == "user")

    if st.button("Give me the infrastructure design", type="primary", disabled=(user_msg_count < 5)):
        with st.spinner("Generating infrastructure design..."):
            st.session_state.builder_chat.append({"role": "user", "content": "yes i want the infrastructure design"})
            user_msg_count = sum(1 for m in st.session_state.builder_chat if m.get("role") == "user")
            
            result = process_builder_chat(st.session_state.builder_chat, infra, user_msg_count)
            
            # Merge dynamically returned "add_services" into infra state
            add_svcs = result.get("add_services", {})
            if isinstance(add_svcs, dict):
                for svc_name, svc_list in add_svcs.items():
                    if svc_name not in infra:
                        infra[svc_name] = []
                    if isinstance(svc_list, list):
                        infra[svc_name].extend(svc_list)
                
            st.session_state.builder_chat.append({"role": "assistant", "content": result.get("message", "I have updated the design.")})
            st.rerun()

    if st.session_state.builder_chat:
        last_msg = st.session_state.builder_chat[-1]
        msg_content = last_msg.get("content") if isinstance(last_msg, dict) else str(last_msg)
        st.info(f"**AI Builder:** {msg_content}")
        
    builder_input = st.chat_input("E.g., set up Migration Hub, or build an EC2 instance", key="builder_input")
    if builder_input:
        st.session_state.builder_chat.append({"role": "user", "content": builder_input})
        user_msg_count = sum(1 for m in st.session_state.builder_chat if m.get("role") == "user")
        
        with st.spinner("Analyzing requirements..."):
            result = process_builder_chat(st.session_state.builder_chat, infra, user_msg_count)
            
            # Merge dynamically returned "add_services" into infra state
            add_svcs = result.get("add_services", {})
            if isinstance(add_svcs, dict):
                for svc_name, svc_list in add_svcs.items():
                    if svc_name not in infra:
                        infra[svc_name] = []
                    if isinstance(svc_list, list):
                        infra[svc_name].extend(svc_list)
                
            st.session_state.builder_chat.append({"role": "assistant", "content": result.get("message", "I have updated the design.")})
            st.rerun()

    st.divider()

    if not infra:
        st.write("Start typing in the chat above to build ANY AWS service!")
        
    # Generic Renderer for all services in infra
    for svc_name, svc_instances in list(infra.items()):
        st.subheader(f"{svc_name} Configuration")
        
        for i, inst in enumerate(list(svc_instances)):
            st.markdown(f"**{svc_name} Instance #{i+1}**")
            
            # Button to remove the entire instance
            if st.button(f"❌ Remove {svc_name} #{i+1}", key=f"rm_svc_{svc_name}_{i}"):
                infra[svc_name].pop(i)
                if not infra[svc_name]:
                    del infra[svc_name]
                st.rerun()

            # Render simple fields and nested lists
            for key in list(inst.keys()):
                val = inst[key]
                
                # If nested list (e.g. Subnets, Tags, Security Groups)
                if isinstance(val, list):
                    st.markdown(f"**↳ {key}**")
                    for j, nested_inst in enumerate(list(val)):
                        n_cols = st.columns([3, 1])
                        with n_cols[0]:
                            if isinstance(nested_inst, dict):
                                for n_key in list(nested_inst.keys()):
                                    if not isinstance(nested_inst[n_key], (list, dict)):
                                        # Field Renderer
                                        cc1, cc2 = st.columns([10, 2])
                                        with cc1:
                                            nested_inst[n_key] = st.text_input(f"{n_key.replace('_', ' ').capitalize()}", str(nested_inst[n_key]), key=f"inp_{svc_name}_{i}_{key}_{j}_{n_key}")
                                        with cc2:
                                            with st.popover("ℹ️", help="Ask AI"):
                                                q = st.text_input(f"Ask about `{n_key}`:", key=f"q_{svc_name}_{i}_{key}_{j}_{n_key}")
                                                if st.button("Ask", key=f"ask_{svc_name}_{i}_{key}_{j}_{n_key}") and q:
                                                    with st.spinner("AI thinking..."):
                                                        res = process_component_chat(f"{svc_name} -> {key} -> {n_key}", q, infra)
                                                        st.write(res.get("message", ""))
                            else:
                                st.write(str(nested_inst))
                        with n_cols[1]:
                            st.write("")
                            if st.button("❌ Remove", key=f"rm_nest_{svc_name}_{i}_{key}_{j}"):
                                inst[key].pop(j)
                                st.rerun()
                elif isinstance(val, dict):
                    pass # skip deep dicts for basic MVP UI
                else:
                    # Simple Field Renderer
                    c1, c2 = st.columns([10, 2])
                    with c1:
                        inst[key] = st.text_input(f"{key.replace('_', ' ').capitalize()}", str(val), key=f"inp_{svc_name}_{i}_{key}")
                    with c2:
                        with st.popover("ℹ️", help="Ask AI"):
                            q = st.text_input(f"Ask about `{key}`:", key=f"q_{svc_name}_{i}_{key}")
                            if st.button("Ask", key=f"ask_{svc_name}_{i}_{key}") and q:
                                with st.spinner("AI thinking..."):
                                    res = process_component_chat(f"{svc_name} -> {key}", q, infra)
                                    st.write(res.get("message", ""))
            
            # Ask specific AI for the entire component container
            with st.expander(f"➕ Explore more `{svc_name}` configurations"):
                comp_q = st.text_input(f"Ask what else to configure for {svc_name}...", key=f"cq_{svc_name}_{i}")
                if st.button("Ask AI", key=f"cb_{svc_name}_{i}") and comp_q:
                    with st.spinner("Thinking..."):
                        cr = process_component_chat(svc_name, comp_q, infra)
                        st.session_state[f"cr_{svc_name}_{i}"] = cr
                
                if f"cr_{svc_name}_{i}" in st.session_state:
                    cr = st.session_state[f"cr_{svc_name}_{i}"]
                    st.info(f"**AI:** {cr.get('message', '')}")
                    sug_fields = cr.get("suggested_fields", {})
                    if sug_fields:
                        st.warning("Suggestions available!")
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            if st.button("🧐 Explain Fields", key=f"ce_{svc_name}_{i}"):
                                with st.spinner("Explaining..."):
                                    st.session_state[f"cx_{svc_name}_{i}"] = process_explain_fields(svc_name, sug_fields)
                        with sc2:
                            if st.button("➕ Add Fields", key=f"ca_{svc_name}_{i}"):
                                for k, v in get_sug_items(sug_fields):
                                    if k not in inst:
                                        inst[k] = str(v)
                                st.rerun()
                        if f"cx_{svc_name}_{i}" in st.session_state:
                            st.success(st.session_state[f"cx_{svc_name}_{i}"])
                            
        st.divider()

# ------------- RIGHT PANEL (GENERIC TREE) -------------
with col3:
    if infra:
        st.markdown("""
        <style>
        [data-testid="column"]:nth-of-type(3) [data-testid="stButton"] button {
            background-color: #ff69b4 !important;
            border-color: #ff69b4 !important;
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        # Add the pink export button floated to the top right structurally
        _, _, b_col = st.columns([1, 1, 2])
        with b_col:
            btn_label = "🔙 View Diagram" if st.session_state.show_terraform else "🚀 Get Terraform YAML"
            if st.button(btn_label, key="tf_export_btn"):
                st.session_state.show_terraform = not st.session_state.show_terraform
                if st.session_state.show_terraform and "terraform_export_cache" in st.session_state:
                    del st.session_state["terraform_export_cache"]
                st.rerun()
                
    if st.session_state.show_terraform:
        st.title("🚀 Terraform Export")
        with st.spinner("Generating perfect Terraform syntax using AWS Bedrock Nova..."):
            if "terraform_export_cache" not in st.session_state:
                tf_code = generate_terraform(st.session_state.infra)
                st.session_state.terraform_export_cache = tf_code
            tf_code = st.session_state.terraform_export_cache
        st.code(tf_code, language="hcl")
    else:
        st.title("🌳 Infrastructure")

        if not infra:
            st.write("*(No components yet)*")

        for svc_name, svc_instances in infra.items():
            st.markdown(f"**{svc_name}**")
            for i, inst in enumerate(svc_instances):
                prefix = "├──" if i < len(svc_instances) - 1 else "└──"
                
                # Pick a main identifier (like name, type, id, cidr) to display cleanly
                ident = inst.get("name", inst.get("type", inst.get("cidr", f"Instance {i+1}")))
                
                with st.expander(f"{prefix} {ident}", expanded=False):
                    for k, v in inst.items():
                        if isinstance(v, list):
                            st.markdown(f"  - **{k}**: *({len(v)} items)*")
                        elif not isinstance(v, dict):
                            st.markdown(f"  - **{k}**: {v}")