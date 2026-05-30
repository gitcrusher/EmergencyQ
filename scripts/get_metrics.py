import mlflow
import os

os.chdir('d:/nlp project')
client = mlflow.tracking.MlflowClient()
experiment = client.get_experiment_by_name('EmergencyQ-DistilBERT')

if experiment:
    runs = client.search_runs(experiment.experiment_id, order_by=['start_time DESC'])
    if runs:
        best_run = runs[0]
        print('\n' + '='*50)
        print('  DISTILBERT BEST METRICS (MLFLOW)')
        print('='*50)
        
        try:
            f1_history = client.get_metric_history(best_run.info.run_id, 'eval_macro_f1')
            acc_history = client.get_metric_history(best_run.info.run_id, 'eval_accuracy')
            
            best_f1 = max([m.value for m in f1_history]) if f1_history else 0
            best_acc = max([m.value for m in acc_history]) if acc_history else 0
            
            print(f'  Best Macro F1 Score : {best_f1 * 100:.2f}%')
            print(f'  Best Accuracy       : {best_acc * 100:.2f}%')
            print('='*50 + '\n')
            
        except Exception as e:
            print('Error fetching history:', e)
    else:
        print('No runs found in this experiment.')
else:
    print('Experiment not found.')
