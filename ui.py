
import streamlit as st


def flash(*messages: tuple[str, str]) -> None:

    st.session_state["_flash"] = list(messages)
    st.rerun()


def show_flash() -> None:

    for kind, text in st.session_state.pop("_flash", []):
        if kind == "success":
            st.success(text)
        elif kind == "warning":
            st.warning(text)
        elif kind == "error":
            st.error(text)
        elif kind == "code":
            st.code(text, language=None)
        else:
            st.info(text)
