import json
import pandas as pd
import numpy as np
from tqdm import tqdm


def read_csv(path, strict_mode=True):
    df = pd.read_csv(path, encoding='utf-8')
    metric_value = df['metric']

    metric_value = [list(json.loads(i.replace('\'', '\"')).values()) for i in metric_value]
    metric_value = [[float(j) for j in i] for i in metric_value]
    id_list = list(df['id'])

    assert len(id_list) == len(metric_value)
    # id_dict = dict(zip(id_list, metric_value))

    value_dict = {}
    if strict_mode:
        for index, values in enumerate(metric_value):
            if len(values) > 1:
                values[0] = values[0] * 1.5
                num = float(np.sum(values))
                if value_dict.get(num) is None:
                    value_dict[num] = set([id_list[index]])
                else:
                    value_dict[num].add(id_list[index])
            else:
                if value_dict.get(values[0]) is None:
                    value_dict[values[0]] = set([id_list[index]])
                else:
                    value_dict[values[0]].add(id_list[index])
    else:
        for index, values in enumerate(metric_value):
            for value in values:
                if value_dict.get(value) is None:
                    value_dict[value] = set([id_list[index]])
                else:
                    value_dict[value].add(id_list[index])
    return df, value_dict


def similar_value():
    df, value_dict = read_csv('./data/Sota_Evaluations.csv')
    filtered_list = []
    for key, value in value_dict.items():
        if len(set(value)) > 1:
            df_data = df.loc[df['id'].isin(value)]
            data_list = df_data['dataset']

            if len(set(data_list)) == len(data_list):
                continue
            else:
                df_dup = df_data[data_list.duplicated()]
                dup_list = list(set(df_dup["dataset"]))
                for dup in dup_list:
                    filtered_list.append(list(df_data.loc[df_data['dataset']==dup, 'id']))

    print(len(filtered_list))
    return filtered_list, df


# def similar_value():
#     df, value_dict, metric_value = read_csv('./data/Sota_Evaluations.csv')
#     final_id = []
#     second_dict = value_dict.copy()
#     print(len(second_dict))
#
#     for id_one, value_one in tqdm(value_dict.items()):
#         one_item = [id_one]
#
#         second_dict.pop(id_one)
#         for id_two, value_two in tqdm(second_dict.items()):
#             value_two.extend(value_one)
#             if len(set(value_two)) < len(value_two):
#                 one_item.append(id_two)
#
#         if len(set(one_item)) > 1:
#             final_id.append(list(set(one_item)))
#     print(final_id)
#     return final_id


if __name__ == "__main__":
    filtered_list, df = similar_value()

    # one value
    filtered_list = [j for i in filtered_list for j in i]
    df_re = pd.DataFrame()
    for i in filtered_list:
        df_re = df_re.append(df.loc[df['id']==i], ignore_index=True)

    df_re.to_csv('./data/sample2.csv', index=False, sep=',', encoding='utf-8')