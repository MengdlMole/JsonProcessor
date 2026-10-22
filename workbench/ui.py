from __future__ import annotations

from html import escape

import streamlit as st

from .models import ToolDefinition


def apply_design_system() -> None:
    st.markdown(
        """
        <style>
        :root {
          --jp-bg: #f6f7fb;
          --jp-surface: #ffffff;
          --jp-border: #e4e7ec;
          --jp-text: #182230;
          --jp-muted: #667085;
          --jp-primary: #465fff;
          --jp-primary-soft: #eef1ff;
          --jp-radius: 12px;
        }
        [data-testid="stAppViewContainer"] { background: var(--jp-bg); }
        [data-testid="stHeader"] { background: rgba(246,247,251,.88); }
        [data-testid="stSidebar"] { border-right: 1px solid var(--jp-border); }
        [data-testid="stSidebar"] > div:first-child { background: #fbfcfe; }
        .block-container { max-width: 1480px; padding-top: 2rem; padding-bottom: 4rem; }
        h1, h2, h3 { color: var(--jp-text); letter-spacing: -0.02em; }
        [data-testid="stVerticalBlockBorderWrapper"] {
          background: var(--jp-surface);
          border-color: var(--jp-border) !important;
          border-radius: var(--jp-radius);
          box-shadow: 0 1px 2px rgba(16,24,40,.03);
        }
        .jp-eyebrow {
          color: var(--jp-primary); font-size: .75rem; font-weight: 700;
          letter-spacing: .08em; text-transform: uppercase; margin-bottom: .35rem;
        }
        .jp-title { margin: 0; color: var(--jp-text); font-size: 2rem; line-height: 1.2; }
        .jp-description { color: var(--jp-muted); margin: .55rem 0 1.5rem; max-width: 860px; }
        .jp-tool-meta { color: var(--jp-muted); font-size: .86rem; margin-top: -.35rem; }
        .jp-badge {
          display: inline-flex; align-items: center; border-radius: 999px;
          padding: .2rem .55rem; margin-right: .35rem; background: var(--jp-primary-soft);
          color: #3448d8; font-size: .75rem; font-weight: 650;
        }
        .jp-section-number {
          display: inline-flex; align-items: center; justify-content: center;
          width: 1.55rem; height: 1.55rem; border-radius: 999px;
          background: var(--jp-primary-soft); color: #3448d8; font-weight: 700;
          margin-right: .45rem; font-size: .8rem;
        }
        .jp-section-title { color: var(--jp-text); font-weight: 700; font-size: 1rem; }
        .jp-section-caption { color: var(--jp-muted); font-size: .82rem; margin: .25rem 0 .8rem 2.05rem; }
        div.stButton > button, div.stDownloadButton > button { border-radius: 9px; }
        div[data-baseweb="select"] > div, textarea, input { border-radius: 9px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, description: str) -> None:
    st.markdown(
        f'<div class="jp-eyebrow">{escape(eyebrow)}</div>'
        f'<h1 class="jp-title">{escape(title)}</h1>'
        f'<p class="jp-description">{escape(description)}</p>',
        unsafe_allow_html=True,
    )


def section_header(number: int, title: str, caption: str = "") -> None:
    st.markdown(
        f'<div><span class="jp-section-number">{number}</span>'
        f'<span class="jp-section-title">{escape(title)}</span></div>'
        + (f'<div class="jp-section-caption">{escape(caption)}</div>' if caption else ""),
        unsafe_allow_html=True,
    )


def tool_header(tool: ToolDefinition) -> None:
    kind = "工作流" if tool.kind == "workflow" else "原子脚本"
    badges = list(dict.fromkeys([kind, *tool.tags]))
    rendered_badges = "".join(f'<span class="jp-badge">{escape(label)}</span>' for label in badges)
    st.markdown(f"### {escape(tool.name)}")
    st.markdown(rendered_badges, unsafe_allow_html=True)
    st.markdown(
        f'<p class="jp-tool-meta">版本 {escape(tool.version)} · {escape(tool.description)}</p>',
        unsafe_allow_html=True,
    )
