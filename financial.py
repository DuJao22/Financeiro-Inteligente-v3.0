from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Transaction, Account
from forms import TransactionForm, AccountForm
from datetime import datetime
from utils import now_brasilia, brasilia_to_utc

financial_bp = Blueprint('financial', __name__)

@financial_bp.route('/cash-flow')
@login_required
def cash_flow():
    # Check plan limits
    features = current_user.get_plan_features()
    transaction_count = Transaction.count_by_user_id(current_user.id)
    
    if features['transactions_limit'] != -1 and transaction_count >= features['transactions_limit']:
        flash('Você atingiu o limite de transações do seu plano. Faça upgrade para continuar.', 'warning')
    
    # Get all transactions
    transactions = Transaction.get_by_user_id(current_user.id)
    
    # Calculate totals
    total_income = sum(float(t.amount) for t in transactions if t.transaction_type == 'income')
    total_expenses = sum(float(t.amount) for t in transactions if t.transaction_type == 'expense')
    current_balance = total_income - total_expenses
    
    return render_template('financial/cash_flow.html',
                         transactions=transactions,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         current_balance=current_balance,
                         features=features)

@financial_bp.route('/add-transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    # Check plan limits
    features = current_user.get_plan_features()
    transaction_count = Transaction.count_by_user_id(current_user.id)
    
    if features['transactions_limit'] != -1 and transaction_count >= features['transactions_limit']:
        flash('Você atingiu o limite de transações do seu plano. Faça upgrade para continuar.', 'error')
        return redirect(url_for('subscription.plans'))
    
    form = TransactionForm()
    if form.validate_on_submit():
        # Convert date from Brasilia to UTC for storage
        if form.date.data:
            transaction_date = datetime.combine(form.date.data, datetime.min.time())
            transaction_date_utc = brasilia_to_utc(transaction_date)
        else:
            transaction_date_utc = brasilia_to_utc(now_brasilia())
        
        transaction = Transaction(
            user_id=current_user.id,
            description=form.description.data,
            amount=form.amount.data,
            transaction_type=form.transaction_type.data,
            category=form.category.data,
            date=transaction_date_utc.isoformat()
        )
        transaction.save()
        
        flash('Transação adicionada com sucesso!', 'success')
        return redirect(url_for('financial.cash_flow'))
    
    # Set default date to today (Brasilia timezone)
    if not form.date.data:
        form.date.data = now_brasilia().date()
    
    # Get all transactions to calculate totals (same as cash_flow function)
    transactions = Transaction.get_by_user_id(current_user.id)
    
    # Calculate totals
    total_income = sum(float(t.amount) for t in transactions if t.transaction_type == 'income')
    total_expenses = sum(float(t.amount) for t in transactions if t.transaction_type == 'expense')
    current_balance = total_income - total_expenses
    
    return render_template('financial/cash_flow.html',
                         form=form,
                         show_form=True,
                         transactions=transactions,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         current_balance=current_balance,
                         features=features)

@financial_bp.route('/accounts')
@login_required
def accounts():
    receivables = Account.get_by_user_id(current_user.id, 'receivable')
    payables = Account.get_by_user_id(current_user.id, 'payable')
    
    # Calculate totals
    total_receivables = sum(float(a.amount) for a in receivables if a.status == 'pending')
    total_payables = sum(float(a.amount) for a in payables if a.status == 'pending')
    
    return render_template('financial/accounts.html',
                         receivables=receivables,
                         payables=payables,
                         total_receivables=total_receivables,
                         total_payables=total_payables)

@financial_bp.route('/add-account', methods=['GET', 'POST'])
@login_required
def add_account():
    form = AccountForm()
    if form.validate_on_submit():
        # Convert due_date from Brasilia to UTC for storage
        if form.due_date.data:
            due_date = datetime.combine(form.due_date.data, datetime.min.time())
            due_date_utc = brasilia_to_utc(due_date)
        else:
            due_date_utc = None
        
        account = Account(
            user_id=current_user.id,
            name=form.name.data,
            account_type=form.account_type.data,
            amount=form.amount.data,
            due_date=due_date_utc.isoformat() if due_date_utc else None
        )
        account.save()
        
        flash('Conta adicionada com sucesso!', 'success')
        return redirect(url_for('financial.accounts'))
    
    # Get accounts data (same as accounts function)
    receivables = Account.get_by_user_id(current_user.id, 'receivable')
    payables = Account.get_by_user_id(current_user.id, 'payable')
    
    # Calculate totals
    total_receivables = sum(float(a.amount) for a in receivables if a.status == 'pending')
    total_payables = sum(float(a.amount) for a in payables if a.status == 'pending')
    
    return render_template('financial/accounts.html',
                         form=form,
                         show_form=True,
                         receivables=receivables,
                         payables=payables,
                         total_receivables=total_receivables,
                         total_payables=total_payables)

@financial_bp.route('/mark-paid/<int:account_id>')
@login_required
def mark_paid(account_id):
    account = Account.get_by_id(account_id, current_user.id)
    if not account:
        flash('Conta não encontrada.', 'error')
        return redirect(url_for('financial.accounts'))
    
    account.status = 'paid'
    account.save()
    
    # Create corresponding transaction
    transaction_type = 'income' if account.account_type == 'receivable' else 'expense'
    transaction = Transaction(
        user_id=current_user.id,
        description=f'Pagamento: {account.name}',
        amount=account.amount,
        transaction_type=transaction_type,
        category='pagamentos',
        date=brasilia_to_utc(now_brasilia()).isoformat()
    )
    transaction.save()
    
    flash('Conta marcada como paga e transação criada!', 'success')
    return redirect(url_for('financial.accounts'))