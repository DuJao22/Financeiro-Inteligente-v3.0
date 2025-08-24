from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database import FinancialGoal
from forms import FinancialGoalForm
from utils import format_currency, utc_to_brasilia
from datetime import datetime

# Create blueprint
goals_bp = Blueprint('goals', __name__, url_prefix='/goals')

@goals_bp.route('/')
@login_required
def goals_list():
    """List all financial goals"""
    active_goals = FinancialGoal.get_by_user_id(current_user.id, is_completed=False)
    completed_goals = FinancialGoal.get_by_user_id(current_user.id, is_completed=True)
    
    # Calculate statistics
    total_target = sum(goal.target_amount for goal in active_goals)
    total_current = sum(goal.current_amount for goal in active_goals)
    overall_progress = (total_current / total_target * 100) if total_target > 0 else 0
    
    return render_template('goals/goals_list.html',
                         active_goals=active_goals,
                         completed_goals=completed_goals,
                         total_target=total_target,
                         total_current=total_current,
                         overall_progress=overall_progress,
                         format_currency=format_currency)

@goals_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_goal():
    """Create new financial goal"""
    form = FinancialGoalForm()
    
    if form.validate_on_submit():
        goal = FinancialGoal(
            user_id=current_user.id,
            title=form.title.data,
            target_amount=float(form.target_amount.data),
            current_amount=float(form.current_amount.data or 0),
            target_date=form.target_date.data,
            created_at=datetime.utcnow()
        )
        goal.save()
        flash(f'Meta "{goal.title}" criada com sucesso!', 'success')
        return redirect(url_for('goals.goals_list'))
    
    return render_template('goals/goal_form.html', form=form, title='Nova Meta Financeira')

@goals_bp.route('/edit/<int:goal_id>', methods=['GET', 'POST'])
@login_required
def edit_goal(goal_id):
    """Edit existing financial goal"""
    goal = FinancialGoal.get_by_id(goal_id)
    if not goal or goal.user_id != current_user.id:
        flash('Meta não encontrada.', 'error')
        return redirect(url_for('goals.goals_list'))
    
    form = FinancialGoalForm(obj=goal)
    
    if form.validate_on_submit():
        goal.title = form.title.data
        goal.target_amount = float(form.target_amount.data)
        goal.current_amount = float(form.current_amount.data or 0)
        goal.target_date = form.target_date.data
        
        # Check if goal is completed
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
            flash(f'🎉 Parabéns! Meta "{goal.title}" foi concluída!', 'success')
        else:
            goal.is_completed = False
        
        goal.save()
        flash('Meta atualizada com sucesso!', 'success')
        return redirect(url_for('goals.goals_list'))
    
    return render_template('goals/goal_form.html', form=form, goal=goal, title='Editar Meta')

@goals_bp.route('/delete/<int:goal_id>', methods=['POST'])
@login_required
def delete_goal(goal_id):
    """Delete financial goal"""
    goal = FinancialGoal.get_by_id(goal_id)
    if not goal or goal.user_id != current_user.id:
        flash('Meta não encontrada.', 'error')
        return redirect(url_for('goals.goals_list'))
    
    goal.delete()
    flash('Meta excluída com sucesso.', 'success')
    return redirect(url_for('goals.goals_list'))

@goals_bp.route('/update_progress/<int:goal_id>', methods=['POST'])
@login_required
def update_progress(goal_id):
    """Update goal progress via AJAX"""
    goal = FinancialGoal.get_by_id(goal_id)
    if not goal or goal.user_id != current_user.id:
        return jsonify({'error': 'Meta não encontrada'}), 404
    
    data = request.get_json()
    new_amount = float(data.get('amount', 0))
    
    if new_amount < 0:
        return jsonify({'error': 'Valor deve ser positivo'}), 400
    
    goal.current_amount = new_amount
    
    # Check if goal is completed
    if goal.current_amount >= goal.target_amount:
        goal.is_completed = True
        message = f'🎉 Meta "{goal.title}" concluída!'
    else:
        goal.is_completed = False
        message = 'Progresso atualizado com sucesso!'
    
    goal.save()
    
    return jsonify({
        'success': True,
        'message': message,
        'progress': goal.get_progress_percentage(),
        'is_completed': goal.is_completed,
        'current_amount': goal.current_amount,
        'formatted_current': format_currency(goal.current_amount)
    })

@goals_bp.route('/complete/<int:goal_id>', methods=['POST'])
@login_required
def complete_goal(goal_id):
    """Mark goal as completed"""
    goal = FinancialGoal.get_by_id(goal_id)
    if not goal or goal.user_id != current_user.id:
        flash('Meta não encontrada.', 'error')
        return redirect(url_for('goals.goals_list'))
    
    goal.current_amount = goal.target_amount
    goal.is_completed = True
    goal.save()
    
    flash(f'🎉 Parabéns! Meta "{goal.title}" foi marcada como concluída!', 'success')
    return redirect(url_for('goals.goals_list'))

@goals_bp.route('/reactivate/<int:goal_id>', methods=['POST'])
@login_required
def reactivate_goal(goal_id):
    """Reactivate completed goal"""
    goal = FinancialGoal.get_by_id(goal_id)
    if not goal or goal.user_id != current_user.id:
        flash('Meta não encontrada.', 'error')
        return redirect(url_for('goals.goals_list'))
    
    goal.is_completed = False
    goal.save()
    
    flash(f'Meta "{goal.title}" foi reativada!', 'info')
    return redirect(url_for('goals.goals_list'))