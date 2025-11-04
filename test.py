import streamlit as st

@st.dialog("Cast your vote")
def vote(item):
    st.write(f"Why is {item} your favorite?")
    reason = st.text_input("Because...")
    if st.button("Submit"):
        st.session_state.vote = {"item": item, "reason": reason}
        st.rerun()


col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Detalhes"):
        vote("A")
with col2:
    if st.button("Editar conta"):
        vote("B")
if "vote" not in st.session_state:
    st.write("Vote for your favorite")

else:
    f"You voted for {st.session_state.vote['item']} because {st.session_state.vote['reason']}"