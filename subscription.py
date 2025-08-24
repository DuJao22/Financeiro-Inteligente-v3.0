from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import User
from database import db_manager
from datetime import datetime, timedelta

subscription_bp = Blueprint('subscription', __name__)

@subscription_bp.route('/plans')
@login_required
def plans():
    plans = [
        {
            'id': 'mei',
            'name': 'Plano MEI',
            'price': 49,
            'description': 'Perfeito para Microempreendedores Individuais',
            'features': [
                'Até 100 transações/mês',
                'Relatórios básicos',
                'Controle de caixa',
                'Contas a pagar/receber',
                'Suporte por email'
            ],
            'popular': False
        },
        {
            'id': 'professional',
            'name': 'Plano Profissional',
            'price': 99,
            'description': 'Para pequenos negócios em crescimento',
            'features': [
                'Até 500 transações/mês',
                'Relatórios avançados',
                'Automações inteligentes',
                'Integração Mercado Pago',
                'Análise de impostos',
                'Suporte prioritário'
            ],
            'popular': True
        },
        {
            'id': 'enterprise',
            'name': 'Plano Empresarial',
            'price': 199,
            'description': 'Para empresas que precisam de mais',
            'features': [
                'Transações ilimitadas',
                'Multiusuário',
                'Acesso para contador',
                'Relatórios personalizados',
                'API completa',
                'Suporte 24/7'
            ],
            'popular': False
        }
    ]
    
    return render_template('subscription/plans.html', plans=plans)

@subscription_bp.route('/checkout/<plan_id>')
@login_required
def checkout(plan_id):
    if plan_id not in ['mei', 'professional', 'enterprise']:
        flash('Plano inválido.', 'error')
        return redirect(url_for('subscription.plans'))
    
    plan_prices = {
        'mei': 49,
        'professional': 99,
        'enterprise': 199
    }
    
    plan_names = {
        'mei': 'Plano MEI',
        'professional': 'Plano Profissional',
        'enterprise': 'Plano Empresarial'
    }
    
    plan_info = {
        'id': plan_id,
        'name': plan_names[plan_id],
        'price': plan_prices[plan_id]
    }
    
    return render_template('subscription/checkout.html', plan=plan_info)

@subscription_bp.route('/activate-plan/<plan_id>')
@login_required
def activate_plan(plan_id):
    """Mock subscription activation (in real app, this would integrate with payment gateway)"""
    if plan_id not in ['mei', 'professional', 'enterprise']:
        flash('Plano inválido.', 'error')
        return redirect(url_for('subscription.plans'))
    
    # Update user subscription in database
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # Set subscription end date to 30 days from now
    end_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    cursor.execute('''
        UPDATE users 
        SET subscription_plan = ?, subscription_status = 'active', subscription_end_date = ?
        WHERE id = ?
    ''', (plan_id, end_date, current_user.id))
    
    conn.commit()
    conn.close()
    
    # Update current_user object
    current_user.subscription_plan = plan_id
    current_user.subscription_status = 'active'
    current_user.subscription_end_date = end_date
    
    plan_names = {
        'mei': 'Plano MEI',
        'professional': 'Plano Profissional',
        'enterprise': 'Plano Empresarial'
    }
    
    flash(f'{plan_names[plan_id]} ativado com sucesso! Obrigado pela sua assinatura.', 'success')
    return redirect(url_for('dashboard.dashboard'))