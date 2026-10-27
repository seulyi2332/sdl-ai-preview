"""Thin view composition to keep the compass interface coherent."""
from compass_board import home_view,goal_view
from compass_study import study_view
from compass_records import records_view
from compass_journal import journal_form,selfcheck


def diary_view(db,owner,client,model):
    journal_form(db,owner,client,model)
    selfcheck(db,owner)
