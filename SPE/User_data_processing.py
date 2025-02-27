import os
import glob
import numpy
# from User_CNN_tools import *
from User_MLP_release import *
from copy import copy
from scipy.signal import medfilt


import pandas as pd
from sklearn.model_selection import train_test_split

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix

def computeEvalMetrics(CM, filename='results', save=False):
    '''
    Compute Precision, Recall & F1 given a Confusion Matrix
    :param CM: confusion matrix
    :param filename: name of output file - only if save is true
    :param save: if results will be stored
    :return: stores confusion matrix if save==True
    '''
    CM = CM + 0.0000000010
    Rec = numpy.zeros((CM.shape[0],))
    Pre = numpy.zeros((CM.shape[0],))
    for ci in range(CM.shape[0]):
        Rec[ci] = CM[ci, ci] / numpy.sum(CM[ci, :])
        Pre[ci] = CM[ci, ci] / numpy.sum(CM[:, ci])
    F1 = 2 * Rec * Pre / (Rec + Pre)

    avg_pre = numpy.mean(Pre)
    avg_rec = numpy.mean(Rec)
    avg_f1 = numpy.mean(F1)

    print('Total CM')
    print(CM)
    print('Pre:', Pre, '- AVG Pre:', avg_pre)
    print('Rec:', Rec, '- AVG Rec:', avg_rec)
    print('F1:', F1, '- AVG F1:', avg_f1)
    if save:
        # Save .npz file
        results = {
            'Confusion_Matrix': CM,
            'Precision': Pre,
            'Recall': Rec,
            'F1_Score': F1,
            'AVG_Precision': avg_pre,
            'AVG_Recall': avg_rec,
            'AVG_F1_Score': avg_f1
        }
        # print("filename ", filename)
        with open(filename + ".txt", 'a') as f:
            # f.write("results:\n")  # Optional: Add a separator or title for each run
            for key, value in results.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")




def postProcessing(predictions,filter=True):
    '''
    Performs post-processing of the raw classifier predictions based on a history of 2 previous windows of length w
    :param predictions: list of predicted labels
    :return: updated predictions after post processing
    '''

    if filter:
        predictions = list(medfilt(predictions,3))

    w = 3 #window length
    step = 1#int(w/3) #window step
    thresh = 0.6 #confidence threshold

    prev3 = None
    prev2 = None #history window 1
    prev1 = None #history window 2
    N=0
    N1 = w
    count = 0
    complete = False #if post processing didnt capture fatigue return predictions full of zeros ie. NO-FATIGUE
    while True:
        count += 1
        if N1 > len(predictions):
            N1 = len(predictions)+1
            complete = True
        x = predictions[N:N1]

        if prev2 != None:
            if x.count(1)/float(w)>=thresh and prev1.count(1)/float(w)>=thresh and prev2.count(1)/float(w)>=thresh :
                post_predictions = [0]*count+[1]*len(predictions[count:])
                break

        prev3 = copy(prev2)
        prev2 = copy(prev1)
        prev1 = copy(x)
        N += step
        N1 += step

        if complete:
            print ('Complete postProcessing')
            post_predictions = [0]*len(predictions)
            break
    return post_predictions

def postProcessing_2(predictions, filter=True):
    if filter:
        predictions = list(medfilt(predictions, 3))
        print(predictions)

    w = 3  # window length
    step = 1  # window step
    base_thresh = 0.6  # base confidence threshold
    alpha = 0.2 # smoothing factor for EMA
    ema_thresh = base_thresh  # initial EMA threshold is the base threshold

    # prev3 = None
    prev2 = None  # history window 1
    prev1 = None  # history window 2
    N = 0
    N1 = w
    count = 0
    complete = False  # if post processing didn't capture fatigue return predictions full of zeros ie. NO-FATIGUE
    fast_thresh = 0.8
    while True:
        count += 1
        if N1 > len(predictions):
            N1 = len(predictions) + 1
            complete = True
        x = predictions[N:N1]
        print('x', N, N1)

        if x.count(1) / float(w) >= fast_thresh:
            print(count)
            index = count - 1
            post_predictions = [0] * index + [1] * (len(predictions) - index)
            print("Triggered fast channel")
            break

        current_ratio = x.count(1) / float(w)
        ema_thresh = alpha * current_ratio + (1 - alpha) * ema_thresh  # Update EMA threshold

        if prev2 != None:
            if x.count(1) / float(w) >= ema_thresh and prev1.count(1) / float(w) >= ema_thresh and prev2.count(1) / float(
                    w) >= ema_thresh:
                index = count - 1
                post_predictions = [0] * index + [1] * len(predictions[index:])
                break
        prev3 = copy(prev2)
        prev2 = copy(prev1)
        prev1 = copy(x)
        N += step
        N1 += step

        if complete:
            print('Complete postProcessing222')
            post_predictions = [0] * len(predictions)
            break

    # print("post_predictions_2",post_predictions)
    return post_predictions

def PrintResults(s,str,CM,CM_post, CM_post2, filename='mlp/105_99'):
    '''
    Prints results before and after post-processing
    '''
    print  (s*20)
    print (str)
    print( "NO-POSTPROCESSING")
    with open(filename + ".txt", 'a') as f:
        f.write("NO-POSTPROCESSING:\n")  # Optional: Add a separator or title for each run
    computeEvalMetrics(CM, filename, save=True)

    print ("POSTPROCESSING")
    with open(filename + ".txt", 'a') as f:
        f.write("POSTPROCESSING-1:\n")
    computeEvalMetrics(CM_post, filename, save=True)

    print ("POSTPROCESSING-2")
    with open(filename + ".txt", 'a') as f:
        f.write("POSTPROCESSING-2:\n")
    computeEvalMetrics(CM_post2, filename, save=True)



def GroupClassification(train, test, classifier_type, num_epochs, batch_size, lr):
    X_train = pd.concat([train[0], train[1]])
    y_train = [0] * len(train[0]) + [1] * len(train[1])
    X_test = pd.concat([test[0], test[1]])
    y_test = [0] * len(test[0]) + [1] * len(test[1])

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    trainer = ModelTrainer(model_type=classifier_type, num_epochs=num_epochs, batch_size=batch_size, lr=lr)
    predictions, probs, cm = trainer.run(X_train, y_train, X_test, y_test)

    post_predictions = postProcessing(predictions)
    post2_predictions = postProcessing_2(predictions)
    print("Predictions:", predictions)
    print("Post-processed Predictions:", post_predictions)
    print("Post2-processed Predictions:", post2_predictions)

    with open("mlp/105_99.txt", 'a') as f:
        f.write("Ground Truth: ")
        for item in y_test:
            f.write(f"{item} ")
        f.write("NO-POSTPROCESSING: ")
        for item in predictions:
            f.write(f"{item} ")
        f.write("Post-1: ")
        for item in post_predictions:
            f.write(f"{item} ")
        f.write("Post-2: ")
        for item in post2_predictions:
            f.write(f"{item} ")
        f.write(f"\n")


    CM = confusion_matrix(y_test, predictions)
    CM_post = confusion_matrix(y_test, post_predictions)
    CM_post_2 = confusion_matrix(y_test, post2_predictions)

    return CM, CM_post, CM_post_2, predictions, post_predictions, post2_predictions




def LoadDataForUser(dirName, user_id):
    data_NF = []
    data_F = []

    for sensor_id in range(1, 10):
        file_name = f"{dirName}/{user_id}_sensor{sensor_id}_labelled.csv"
        try:
            data = pd.read_csv(file_name, header=None)
            nf_rows = data[data.iloc[:, -1] == 0].iloc[:, :-1]
            f_rows = data[data.iloc[:, -1] == 1].iloc[:, :-1]
            if not nf_rows.empty:
                data_NF.append(nf_rows)
            if not f_rows.empty:
                data_F.append(f_rows)
        except FileNotFoundError:
            print(f"File not found: {file_name}, skipping...")

    if data_NF:
        data_NF = pd.concat(data_NF).reset_index(drop=True)
    if data_F:
        data_F = pd.concat(data_F).reset_index(drop=True)

    return data_NF, data_F


def SplitData(data_NF, data_F, test_size=0.1):
    train_data_NF, test_data_NF = train_test_split(data_NF, test_size=test_size, random_state=42)
    train_data_F, test_data_F = train_test_split(data_F, test_size=test_size, random_state=42)
    return train_data_NF, train_data_F, test_data_NF, test_data_F

def SingleUserEvaluation(dirName, classifier, num_epochs, batch_size, lr):
    CM_avg = numpy.zeros((2, 2))
    CM_avg_post = numpy.zeros((2, 2))
    CM_avg_post2 = numpy.zeros((2, 2))

    for user_id in [f"{i:02d}" for i in range(1, 31)]:
        print("\nTesting on user:", user_id)
        with open("mlp/105_99.txt", 'a') as f:
            f.write(user_id+":\n")
        data_NF, data_F = LoadDataForUser(dirName, user_id)
        print(f"Data sizes - NF: {len(data_NF)}, F: {len(data_F)}")

        if len(data_NF) > 0 and len(data_F) > 0:
            train_data_NF, train_data_F, test_data_NF, test_data_F = SplitData(data_NF, data_F)
            print(f"Training on {len(train_data_NF)} NF and {len(train_data_F)} F samples.")
            print(f"Testing on {len(test_data_NF)} NF and {len(test_data_F)} F samples.")

            CM, CM_post, CM_post2, predictions, post_predictions, post2_predictions = GroupClassification(
                [train_data_NF, train_data_F], [test_data_NF, test_data_F],
                classifier, num_epochs, batch_size, lr)

            CM_avg += CM
            CM_avg_post += CM_post
            CM_avg_post2 += CM_post2
            PrintResults('-', f"RESULTS FOR USER {user_id}", CM, CM_post, CM_post2)
        else:
            print("No sufficient data for user:", user_id)
    PrintResults('+', "TOTAL RESULTS ACROSS ALL USERS", CM_avg, CM_avg_post, CM_avg_post2)
