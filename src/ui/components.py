import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Optional, List, Dict, Any
from ..utils.formatting import format_currency, format_percentage

def render_kpi_card(
    title: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None
):
    """Renderiza una tarjeta KPI con estilo estilizado."""
    st.metric(label=title, value=value, delta=delta, delta_color=delta_color, help=help_text)

def plot_cashflow_bar(df_monthly: pd.DataFrame, currency_symbol: str = "€") -> go.Figure:
    """Gráfico de barras agrupadas comparando Ingresos vs Gastos vs Inversiones por mes."""
    fig = go.Figure()
    
    if not df_monthly.empty:
        if 'income' in df_monthly.columns:
            fig.add_trace(go.Bar(
                x=df_monthly['month'],
                y=df_monthly['income'],
                name='Ingresos',
                marker_color='#10B981',
                text=[format_currency(val, currency_symbol) for val in df_monthly['income']],
                textposition='auto'
            ))
        if 'expense' in df_monthly.columns:
            fig.add_trace(go.Bar(
                x=df_monthly['month'],
                y=df_monthly['expense'],
                name='Gastos',
                marker_color='#EF4444',
                text=[format_currency(val, currency_symbol) for val in df_monthly['expense']],
                textposition='auto'
            ))
        if 'investment' in df_monthly.columns:
            fig.add_trace(go.Bar(
                x=df_monthly['month'],
                y=df_monthly['investment'],
                name='Inversiones',
                marker_color='#6366F1',
                text=[format_currency(val, currency_symbol) for val in df_monthly['investment']],
                textposition='auto'
            ))

    fig.update_layout(
        barmode='group',
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
        xaxis=dict(showgrid=False)
    )
    return fig

def plot_expense_donut(df_categories: pd.DataFrame, currency_symbol: str = "€") -> go.Figure:
    """Gráfico Donut de gastos desglosados por categoría."""
    if df_categories.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sin gastos registrados", showarrow=False)
        return fig

    fig = px.pie(
        df_categories,
        names='category_name',
        values='amount',
        hole=0.55,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate="<b>%{label}</b><br>Gasto: %{value:,.2f} " + currency_symbol + "<br>Porcentaje: %{percent}<extra></extra>"
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def plot_net_worth_trend(df_history: pd.DataFrame, currency_symbol: str = "€") -> go.Figure:
    """Gráfico de evolución temporal del Patrimonio Neto y Activos/Pasivos."""
    fig = go.Figure()
    if not df_history.empty:
        fig.add_trace(go.Scatter(
            x=df_history['date'],
            y=df_history['net_worth'],
            mode='lines+markers',
            name='Patrimonio Neto',
            line=dict(color='#6366F1', width=3),
            fill='tozeroy',
            fillcolor='rgba(99, 102, 241, 0.1)'
        ))
        fig.add_trace(go.Scatter(
            x=df_history['date'],
            y=df_history['total_assets'],
            mode='lines',
            name='Total Activos',
            line=dict(color='#10B981', width=2, dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=df_history['date'],
            y=df_history['total_liabilities'],
            mode='lines',
            name='Total Pasivos (Deuda)',
            line=dict(color='#EF4444', width=2, dash='dot')
        ))

    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
        xaxis=dict(showgrid=False)
    )
    return fig

def plot_50_30_20_gauge(actual_data: Dict[str, Any], currency_symbol: str = "€") -> go.Figure:
    """Gráfico de barras comparando objetivo 50/30/20 vs distribución real."""
    categories = ['Necesidades (50%)', 'Deseos / Ocio (30%)', 'Ahorro / Inversión (20%)']
    actual_pcts = [
        actual_data['needs']['pct'],
        actual_data['wants']['pct'],
        actual_data['savings']['pct']
    ]
    target_pcts = [50.0, 30.0, 20.0]
    actual_amounts = [
        actual_data['needs']['actual'],
        actual_data['wants']['actual'],
        actual_data['savings']['actual']
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Real (%)',
        x=categories,
        y=actual_pcts,
        marker_color=['#3B82F6', '#F59E0B', '#10B981'],
        text=[f"{pct:.1f}% ({format_currency(amt, currency_symbol)})" for pct, amt in zip(actual_pcts, actual_amounts)],
        textposition='auto'
    ))
    fig.add_trace(go.Bar(
        name='Objetivo Ideal (%)',
        x=categories,
        y=target_pcts,
        marker_color='rgba(156, 163, 175, 0.4)',
        text=[f"{pct:.0f}%" for pct in target_pcts],
        textposition='auto'
    ))

    fig.update_layout(
        barmode='group',
        yaxis=dict(title='Porcentaje (%)', range=[0, max(max(actual_pcts + [50]) * 1.15, 60)]),
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig
