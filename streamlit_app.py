"""Dashboard de auditoría no-decisorio para demo D2 del jurado (ADR-009).

Este dashboard NUNCA modifica el score. Solo:
1. Analizar — corre ``RuleEngine`` sobre un contrato consultado en SECOP II.
2. Modelo usado — invoca ``route`` para mostrar metadata (Anthropic vs Ollama).
3. Impugnar — form que llama ``POST /contest`` (Pack 4 Responsiveness).

Uso: ``streamlit run streamlit_app.py --server.port 8501``
"""

from __future__ import annotations

import asyncio

import httpx
import streamlit as st

from src.config import get_settings
from src.detection.llm_router import RouterError, route
from src.detection.rules import RuleEngine
from src.ingestion.adapters import SecopAdapter
from src.ingestion.normalizer import Contract

API_BASE_URL = "http://localhost:8000"


@st.cache_resource
def get_engine() -> RuleEngine:
    return RuleEngine()


def _severity_badge(weight: float) -> str:
    if weight >= 0.7:
        return f"🔴 alta ({weight:.2f})"
    if weight >= 0.4:
        return f"🟡 media ({weight:.2f})"
    return f"🟢 baja ({weight:.2f})"


async def _fetch_one(contract_id: str) -> dict | None:
    adapter = SecopAdapter()
    async with adapter.client:
        return await adapter.client.fetch_contract(contract_id)


st.set_page_config(page_title="GobIA Auditor", layout="wide")
st.title("🔍 GobIA Auditor — Dashboard de auditoría")
st.caption(
    "Engine MIT entregable al MinTIC · Hackathon Nacional Colombia 5.0. "
    "Este dashboard NO modifica el score automáticamente (ADR-009). "
    "CONSTITUTION §10 — toda revisión de impugnaciones es humana."
)

tab_analyze, tab_model, tab_contest = st.tabs(
    ["🔎 Analizar", "🤖 Modelo usado", "📨 Impugnar"]
)

# ---------------------------------------------------------------------------
# Tab 1 — Analizar
# ---------------------------------------------------------------------------
with tab_analyze:
    st.subheader("Analizar un contrato SECOP II")
    contract_id = st.text_input(
        "id_contrato",
        placeholder="CO1.PCCNTR.123456",
        help=(
            "Identificador del contrato como aparece en SECOP II "
            "(campo id_contrato del dataset jbjy-vk9h)."
        ),
    )
    if st.button("Analizar", disabled=not contract_id):
        with st.spinner("Consultando SECOP II..."):
            try:
                raw = asyncio.run(_fetch_one(contract_id.strip()))
            except Exception as e:  # noqa: BLE001
                st.error(f"Error consultando SECOP: {e}")
                raw = None

        if raw is None:
            st.warning(
                "Contrato no encontrado o SECOP no respondió. "
                "Verificá el id o reintentá."
            )
        else:
            adapter = SecopAdapter()
            contract = adapter.normalize(raw)
            assert isinstance(contract, Contract)
            hits = get_engine().evaluate([contract])

            col_score, col_meta = st.columns([1, 2])
            score = (
                min(1.0, sum(h.weight for h in hits) / len(hits))
                if hits
                else 0.0
            )
            col_score.metric("Score de opacidad", f"{score:.2f}")
            col_meta.write(
                {
                    "id": contract.id,
                    "entidad": contract.entity,
                    "proveedor": contract.contractor,
                    "valor": str(contract.value),
                    "modalidad": contract.modality,
                    "url_fuente": contract.source_url,
                }
            )

            if not hits:
                st.success(
                    "No se activaron banderas en este contrato (signal=0)."
                )
            else:
                st.subheader("Banderas activadas")
                table_rows = [
                    {
                        "Regla": h.rule_id,
                        "Severidad": _severity_badge(h.weight),
                        "Rationale": h.rationale,
                    }
                    for h in hits
                ]
                st.table(table_rows)
                for h in hits:
                    with st.expander(
                        f"Detalle {h.rule_id} (weight={h.weight:.2f})"
                    ):
                        st.markdown(f"**Rationale:** {h.rationale}")
                        st.markdown(
                            "**Cita legal aplicable:** ver "
                            "`docs/opacity-signals.md` y `docs/examples/`."
                        )
            if contract.source_url:
                st.markdown(f"[Ver contrato en SECOP]({contract.source_url})")


# ---------------------------------------------------------------------------
# Tab 2 — Modelo usado
# ---------------------------------------------------------------------------
with tab_model:
    st.subheader("Probar el LLM Router (Anthropic → Ollama fallback)")
    settings = get_settings()
    col_l, col_r = st.columns(2)
    col_l.write(
        {
            "OFFLINE_MODE": settings.offline_mode,
            "anthropic_api_key_set": bool(settings.anthropic_api_key),
            "ollama_base_url": settings.ollama_base_url,
        }
    )
    if col_r.button("Probar router con prompt de prueba"):
        try:
            result = asyncio.run(
                route(
                    "Devuelve solo el número 0.5",
                    task_type="dashboard-probe",
                    max_tokens=8,
                )
            )
            st.success("Llamada OK")
            st.json(result)
        except RouterError as e:
            st.error(f"Ambos proveedores caídos: {e}")
        except Exception as e:  # noqa: BLE001
            st.error(f"Error inesperado: {e}")


# ---------------------------------------------------------------------------
# Tab 3 — Impugnar
# ---------------------------------------------------------------------------
with tab_contest:
    st.subheader("Impugnar un hallazgo (Pack 4 Responsiveness)")
    st.caption(
        "Esta impugnación llega a la API local en `localhost:8000/contest`. "
        "El sistema NO decide; un humano revisa cada caso en máximo 7 días "
        "hábiles (CONSTITUTION §10)."
    )
    with st.form("contest_form"):
        cid = st.text_input("id_contrato")
        role = st.selectbox(
            "Tu rol",
            ("citizen", "contractor", "entity", "veedor"),
        )
        email = st.text_input("Email de contacto (opcional)")
        reason = st.text_area(
            "Motivo de la impugnación (mínimo 10 caracteres)",
            height=140,
        )
        submitted = st.form_submit_button("Enviar impugnación")

    if submitted:
        try:
            resp = httpx.post(
                f"{API_BASE_URL}/contest",
                json={
                    "contract_id": cid,
                    "reason": reason,
                    "contestant_email": email or None,
                    "contestant_role": role,
                },
                timeout=10.0,
            )
        except httpx.RequestError as e:
            st.error(
                f"No pude contactar la API en {API_BASE_URL}: {e}. "
                "Verificá que `uvicorn src.api.main:app --port 8000` "
                "esté corriendo."
            )
        else:
            if resp.status_code == 201:
                st.success("Impugnación recibida.")
                st.json(resp.json())
            else:
                st.error(f"{resp.status_code}: {resp.text}")


st.markdown("---")
st.caption(
    "💚 [github.com/MNC-Consultoria/gobia-auditor]"
    "(https://github.com) — Engine MIT entregable al MinTIC."
)
