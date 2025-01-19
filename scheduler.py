import schedule
import time
from models.user_model import UserModel
from services.summary_service import SummaryService
from services.incremental_learning_service import IncrementalLearningService

def job():
    users = UserModel.get_users_with_yesterday_date()
    for user in users:
        # Check if the user has already been trained
        if not user.is_trained:
            summary = SummaryService.summarize_user_data(user)
            IncrementalLearningService.perform_incremental_learning(summary)
            # Mark user as trained
            user.is_trained = True
            user.save()

# Schedule the job to run daily at 00:01
schedule.every().day.at("00:01").do(job)