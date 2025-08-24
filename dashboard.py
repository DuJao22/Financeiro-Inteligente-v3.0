from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from database import Transaction, Account, FinancialGoal
from database import db_manager
from datetime import datetime, timedelta
import calendar

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def dashboard():
    # Check subscription status
    if not current_user.is_subscription_active():
        if current_user.subscription_status == 'trial' and current_user.is_trial_expired():
            return render_template('subscription/plans.html', 
                                 message='Seu período de teste expirou. Escolha um plano para continuar.')
    
    # Get dashboard data
    today = datetime.utcnow()
    current_month = today.month
    current_year = today.year
    
    # Monthly summary
    monthly_income, monthly_expenses = Transaction.get_monthly_summary(
        current_user.id, current_month, current_year)
    monthly_balance = monthly_income - monthly_expenses
    
    # Recent transactions
    recent_transactions = Transaction.get_by_user_id(current_user.id, limit=5)
    
    # Accounts summary
    pending_receivables = Account.get_pending_total(current_user.id, 'receivable')
    pending_payables = Account.get_pending_total(current_user.id, 'payable')
    
    # Financial goals
    goals = FinancialGoal.get_by_user_id(current_user.id, is_completed=False)
    goals_summary = {
        'total_goals': len(goals),
        'total_target': sum(goal.target_amount for goal in goals),
        'total_current': sum(goal.current_amount for goal in goals),
        'average_progress': sum(goal.get_progress_percentage() for goal in goals) / len(goals) if goals else 0
    }
    
    # Calculate user level and progress (gamification)
    transaction_count = Transaction.count_by_user_id(current_user.id)
    user_level = min(10, (transaction_count // 10) + 1)
    level_progress = (transaction_count % 10) * 10
    
    return render_template('dashboard/dashboard.html',
                         monthly_income=monthly_income,
                         monthly_expenses=monthly_expenses,
                         monthly_balance=monthly_balance,
                         recent_transactions=recent_transactions,
                         pending_receivables=pending_receivables,
                         pending_payables=pending_payables,
                         goals=goals,
                         goals_summary=goals_summary,
                         user_level=user_level,
                         level_progress=level_progress,
                         current_month=calendar.month_name[current_month])

@dashboard_bp.route('/chart-data')
@login_required
def chart_data():
    """Provide data for dashboard charts"""
    today = datetime.utcnow()
    
    # Get last 6 months data
    months_data = []
    for i in range(6):
        month_date = today - timedelta(days=30*i)
        month = month_date.month
        year = month_date.year
        
        income, expenses = Transaction.get_monthly_summary(current_user.id, month, year)
        
        months_data.append({
            'month': calendar.month_name[month][:3],
            'income': float(income),
            'expenses': float(expenses)
        })
    
    months_data.reverse()
    
    return jsonify({
        'months': [m['month'] for m in months_data],
        'income': [m['income'] for m in months_data],
        'expenses': [m['expenses'] for m in months_data]
    })