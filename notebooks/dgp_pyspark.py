# %% [markdown]
# # Setup

# %%
spark

# %%
# %info

# %%
from functools import reduce
import pyspark.sql.functions as F
from pyspark.sql import Window
from pyspark.sql import DataFrame


# %%
def _get_operator(_str):
    if 0 < len(_str):
        op = ' + '
    else:
        op = ''
    return op


# %% [markdown]
# ## Setup Snowflake Connection

# %%
import snowflake.connector
import getpass

# Snowflake credentials and directories

SNOWFLAKE_CREDS_DICT = {
}

SNOWFLAKE_SESH_DICT = {
}

SNOWFLAKE_WRITE_FROM_SPARK_DICT = {
    'sfURL':SNOWFLAKE_CREDS_DICT['account'] + '.snowflakecomputing.com',
    'sfUser':SNOWFLAKE_CREDS_DICT['user'],
    'sfRole':SNOWFLAKE_CREDS_DICT['role'],
    'sfPassword':SNOWFLAKE_CREDS_DICT['password'],
    'sfDatabase':SNOWFLAKE_SESH_DICT['database'],
    'sfSchema':SNOWFLAKE_SESH_DICT['schema'],
    'sfWarehouse':SNOWFLAKE_SESH_DICT['warehouse'],
    'tracing':'All',
}

SNOWFLAKE_CONNECT_FROM_SPARK_DICT = SNOWFLAKE_CREDS_DICT.copy()
SNOWFLAKE_CONNECT_FROM_SPARK_DICT.update(SNOWFLAKE_SESH_DICT)

# write a Spark dataframe to a NEW (non-temporary) table on Snowflake
def sf_write_spark_df_to_snowflake_new_table(spark_df, table):
    (spark_df.write.format('net.snowflake.spark.snowflake')
     .options(**SNOWFLAKE_WRITE_FROM_SPARK_DICT)
     .option('dbtable',table)
     .mode('overwrite')
     .save())


# %% [markdown]
# # Load Parquets From s3

# %%
# df_patient = spark.read.parquet('s3a://acic-causality-challenge-2022/parquet/patient')
df_patient_year = spark.read.parquet('s3a://acic-causality-challenge-2022/parquet/patient_year')
df_patient_joined = spark.read.parquet('s3a://acic-causality-challenge-2022/patient_joined')
# df_practice = spark.read.parquet('s3a://acic-causality-challenge-2022/parquet/practice')
df_practice_year = spark.read.parquet('s3a://acic-causality-challenge-2022/parquet/practice_year')
df_practice_joined = spark.read.parquet('s3a://acic-causality-challenge-2022/practice_joined')

# %% [markdown]
# # Generate New DGPs
# Let's just keep it simple and only use the first pretreatment year (1,2) to compute the new values. This will drop some patients (~20%), but should be fine.

# %% [markdown]
# ## Setup Base Variables

# %% [markdown]
# ### Practice

# %%
df_practice_base = (df_practice_joined
    .withColumn('minYear', F.min('year').over(Window.partitionBy('dataset_num', 'id_practice')))
    .where((F.col('year') == F.col('minYear')) & F.col('year').isin([1,2]))
    .select(['dataset_num', 'id_practice',
             'n_patients', 'X1', 'X2_A', 'X2_B', 'X2_C', 'X3', 'X4_A', 'X4_B', 'X4_C', 'X5', 'X6', 'X7', 'X8', 'X9',
             'V1_avg', 'V2_avg', 'V3_avg', 'V4_avg', 'V5_A_avg', 'V5_B_avg', 'V5_C_avg']
           )
)

df_practice_base.persist();
print(f'{df_practice_base.count():,}')

# %%
print(f"{df_practice_joined.select('dataset_num', 'id_practice').distinct().count():,}")

# %% [markdown]
# ### Patient

# %%
df_patient_base = (df_patient_joined
    .withColumn('minYear', F.min('year').over(Window.partitionBy('dataset_num', 'id_patient')))
    .where((F.col('year') == F.col('minYear')) & F.col('year').isin([1,2]))
    .withColumnRenamed('year', 'year_original')
    .withColumnRenamed('Y', 'Y_original')
    .withColumn('year', F.lit(0))
    .join(df_practice_base, ['dataset_num', 'id_practice'], 'left')
    .select(['dataset_num', 'id_practice', 'id_patient',
             'year_original', 'year', 'Y_original',
             'n_patients', 'X1', 'X2_A', 'X2_B', 'X2_C', 'X3', 'X4_A', 'X4_B', 'X4_C', 'X5', 'X6', 'X7', 'X8', 'X9',
             'V1', 'V2', 'V3', 'V4', 'V5_A', 'V5_B', 'V5_C']
           )
)

df_patient_base.persist();
print(f'{df_patient_base.count():,}')

# %%
n_distinct_patients_all = df_patient_joined.select('dataset_num', 'id_patient').distinct().count()
n_distinct_patients_pre = df_patient_joined.where(F.col('year').isin([1,2])).select('dataset_num', 'id_patient').distinct().count()

# %%
print(f'n_distinct_patients_all = {n_distinct_patients_all:,}')
print(f'n_distinct_patients_pre = {n_distinct_patients_pre:,}')
print()
print(f'Dropping {(n_distinct_patients_all-n_distinct_patients_pre)/n_distinct_patients_all:.2%} of original patients, across all realizations')

# %%
df_patient_base.groupBy('year_original').agg(F.count('*').alias('n')).orderBy('year_original').toPandas()

# %% [markdown]
# ## Simulate Z
#
# $Z \sim \mathrm{Bernoulli}(p)$  
# where  
# $\mathrm{logit}(p) = f(X, V_{\mathrm{Avg}}) \equiv t$  
#
# $\implies$  
#
# $Z = p < U$  
# $p = 1/(1+\exp(-t))$  
# $U \sim \mathrm{Uniform}(0,1)$  

# %% [markdown]
# ### Set Parameters

# %%
Z_DGP_params = {
    1 : {
        'intercept': -1.5,
        'X1': -0.1,
        'X4_B': -0.1,
        'X4_C': 0.3,
        'X5': 0.2,
        'X7': 0.2,
        'X8': 0.5,
        'X4_B*X8': 0.2,
        'X4_C*X8': -0.6,
    },
    2 : {
        'intercept': -1.3,
        'X1': -0.1,
        'X4_B': -0.2,
        'X4_C': 0.4,
        'X5': 0.2,
        'X7': 0.2,
        'X8': 0.5,
        'X4_B*X8': 0.4,
        'X4_C*X8': -0.6,
    },
}

# %% [markdown]
# ### Run

# %%
df_DFP_Z = df_practice_base.alias('df_DFP_Z')

Z_join_cols = ['dataset_num', 'id_practice']

iseed = 42

Z_cols = []
for iZ_DGP,Z_DGP_param in Z_DGP_params.items():
    # build expr to create t
    t_expr = ''
    for col,weight in Z_DGP_param.items():
        op = _get_operator(t_expr)
        if col == 'intercept':
            t_expr = f'{op}{weight}'
        elif weight != 0:
            t_expr = f'{t_expr}{op}{weight}*{col}'

    print(f'For iZ_DGP = {iZ_DGP}, t = {t_expr}')

    Z_col = f'Z_DGP_{iZ_DGP}'
    df_DFP_Z = (df_DFP_Z
        .withColumn('t', F.expr(t_expr))
        .withColumn(Z_col, F.when(1./(1.+F.exp(-F.col('t'))) < F.rand(seed=iseed), 1).otherwise(0))
        .drop('t')
    )
    Z_cols.append(Z_col)

    iseed += 1

    dfp_Z_counts = df_DFP_Z.groupBy(Z_col).agg(F.count('*').alias('n_patients')).orderBy(Z_col).toPandas()
    dfp_Z_counts['percent'] = 100.*dfp_Z_counts['n_patients'] / dfp_Z_counts['n_patients'].sum()
    print(dfp_Z_counts)

df_DFP_Z_complete = df_DFP_Z.select(Z_join_cols+Z_cols)

df_DFP_Z_complete.persist();
print(f'{df_DFP_Z_complete.count():,}')

# %%
df_DFP_Z_complete.limit(5).toPandas()

# %% [markdown]
# ## Simulate Y
#
# $Y_{1} = Y_{min(1,2)}^{\mathrm{Original}} + u \log(U_{i})$  
# then  
# $Y_{i} = T\,Y_{i-1} + (1-T) \, y_{i} + u \log(U_{i})$  
# for $i=2,3,4$  
# $T \sim \mathrm{Bernoulli}(p_{T})$  
#
# $y_{i} = -\exp(\eta_{i}) \log(U_{i})$  
# $U \sim \mathrm{Uniform}(0,1)$  
# $\eta_{i} \equiv f(i,X,V,\mathrm{post})$  
#
# $\mathrm{post} = 1$ if $Z = 1$ and $i = 3, 4$, and $0$ otherwise  
# Use all $Z$'s from prior step  

# %% [markdown]
# ### Set Parameters

# %%
Y_DGP_params = {
    1 : {
        'u_noise': -20.,
        'p_T': 0.5,
        'Z': [0, 0, -0.05, -0.05],
        'eta': {
            'intercept': [6.6, 6.6, 6.8, 6.8],
            'X8': [-0.2, -0.2, -0.2, -0.2],
            'V4': [0.3, 0.3, 0.5, 0.5],
        },
    },
    2 : {
        'u_noise': -20.,
        'p_T': 0.5,
        'Z': [0, 0, -0.1, -0.1],
        'eta': {
            'intercept': [6.6, 6.6, 6.8, 6.8],
            'X8': [-0.2, -0.2, -0.2, -0.2],
            'V4': [0.3, 0.3, 0.5, 0.5],
        },
    },
}

# %% [markdown]
# ### Run

# %%
df_DFP_Y = df_patient_base.join(df_DFP_Z_complete, Z_join_cols, 'left')

Y_join_cols = ['dataset_num', 'id_practice', 'id_patient', 'year'] # id_practice is not really required, but nice to have
Y_features_X_V = ['n_patients', 'X1', 'X2_A', 'X2_B', 'X2_C', 'X3', 'X4_A', 'X4_B', 'X4_C', 'X5', 'X6', 'X7', 'X8', 'X9', 'V1', 'V2', 'V3', 'V4', 'V5_A', 'V5_B', 'V5_C']

iseed - 1042

Y_results = {}
for iY_DGP,Y_DGP_param in Y_DGP_params.items():
    u_noise = Y_DGP_param.get('u_noise', 0.)

    for iZ_col,Z_col in enumerate(Z_cols):
        Y_col = f'Y_DGP_{iY_DGP}_with_{Z_col}'

        df_lagged = df_DFP_Y.withColumn(Y_col, F.col('Y_original'))

        Z_col_with_post = [Z_col, f'post_{Z_col}']
        Y_results_cols = [Y_col, f'{Y_col}_counterfactual', f'eta_{Y_col}']
        cols_of_df_year = Y_join_cols+Z_col_with_post+Y_results_cols+Y_features_X_V

        df_years = []
        for year in range(1,5):

            # build expr to create eta
            eta_expr_base = ''
            for col,weight_array in Y_DGP_param.get('eta', {}).items():
                op = _get_operator(eta_expr_base)
                if col == 'intercept':
                    eta_expr_base = f'{op}{weight_array[year-1]}'
                elif weight != 0:
                        eta_expr_base = f'{eta_expr_base}{op}{weight_array[year-1]}*{col}'

            # add the Z component
            Z_weight = Y_DGP_param.get('Z', [0,0,0,0])[year-1]
            op = _get_operator(eta_expr_base)

            eta_expr = f'{eta_expr_base}{op}{Z_weight}*post_{Z_col}'
            eta_expr_counterfactual = f'{eta_expr_base}{op}{Z_weight}*post_{Z_col}_counterfactual'

            print(f'For Y_col = {Y_col}, year = {year}, u_noise = {u_noise}, eta = {eta_expr}')

            df_year = (df_lagged
                .where(F.col('year') == year-1)
                .withColumnRenamed(Y_col, 'Y_lag_1')
                .withColumnRenamed(f'{Y_col}_counterfactual', 'Y_lag_1_counterfactual')
                .withColumn('year', F.lit(year))
                .withColumn(f'post_{Z_col}', F.col(Z_col) if year in [3,4] else F.lit(0) )
                .withColumn(f'post_{Z_col}_counterfactual',
                    F.when((F.col('year').isin([3,4])) & (F.col(f'post_{Z_col}') == 0), F.lit(1))
                    .when(F.col('year').isin([3,4]) & (F.col(f'post_{Z_col}') == 1), F.lit(0))
                    .otherwise(F.lit(0))
                )
                .withColumn(f'eta_{Y_col}', F.expr(eta_expr))
                .withColumn(f'eta_{Y_col}_counterfactual', F.expr(eta_expr_counterfactual))
            )

            # compute Y columns
            # note that Y and Y_counterfactual can have different values, even in year 1 and 2, due to their different random noise seeds
            if year == 1:
                df_year = (df_year
                    .withColumn(Y_col, F.col('Y_lag_1') + u_noise*F.log(F.rand(seed=iseed)))
                    .withColumn(f'{Y_col}_counterfactual', F.col('Y_lag_1') + u_noise*F.log(F.rand(seed=iseed+1)))
                )
                iseed += 2

            else:
                df_year = (df_year
                    .withColumn('T', F.when( Y_DGP_param.get('p_T', 0.5) < F.rand(seed=iseed), 1).otherwise(0))
                    .withColumn('T_counterfactual', F.when( Y_DGP_param.get('p_T', 0.5) < F.rand(seed=iseed+1), 1).otherwise(0))

                    .withColumn('y', -F.exp(F.col(f'eta_{Y_col}'))*F.log(F.rand(seed=iseed+2)) )
                    .withColumn('y_counterfactual', -F.exp(F.col(f'eta_{Y_col}_counterfactual'))*F.log(F.rand(seed=iseed+3)) )

                    .withColumn(Y_col, F.col('T')*F.col('Y_lag_1') + (1-F.col('T'))*F.col('y') + u_noise*F.log(F.rand(seed=iseed+4)))
                    .withColumn(f'{Y_col}_counterfactual', F.col('T_counterfactual')*F.col('Y_lag_1_counterfactual') + (1-F.col('T_counterfactual'))*F.col('y_counterfactual') + u_noise*F.log(F.rand(seed=iseed+5)))
                )
                iseed += 6

            # done with this year, save results
            df_years.append(df_year.select(cols_of_df_year))
            df_lagged = reduce(DataFrame.unionAll, df_years)

        # done with this Y, save results
        Y_results[Y_col] = {'Z_col_with_post': Z_col_with_post,
                            'Y_results_cols': Y_results_cols,
                           'df': df_lagged.select([col for col in cols_of_df_year if col not in Y_features_X_V]),
                          }

# combine results from multiple Y_results into one df
# need these steps to get the columns right due to duplicate Y_join_cols, Z_col_with_post
df_DFP_Y_complete = Y_results[list(Y_results.keys())[0]]['df'].select(Y_join_cols)

Z_col_with_post_flat = []
Y_results_cols_flat = []
for Y_col,_dict in Y_results.items():
    Z_col_with_post = _dict['Z_col_with_post']
    if set(Z_col_with_post).issubset(set(df_DFP_Y_complete.columns)):
        # we already have these Z cols, so drop them
        Z_col_with_post = []
    Z_col_with_post_flat += Z_col_with_post

    Y_results_cols = _dict['Y_results_cols']
    Y_results_cols_flat += Y_results_cols

    df_DFP_Y_complete = df_DFP_Y_complete.join(_dict['df'].select(Y_join_cols+Z_col_with_post+Y_results_cols), Y_join_cols, 'left')

df_DFP_Y_complete = df_DFP_Y_complete.select(Y_join_cols+Z_col_with_post_flat+Y_results_cols_flat)

df_DFP_Y_complete.persist();
print(f'{df_DFP_Y_complete.count():,}')


# %%
df_DFP_Y_complete.where(F.col('year') == 1).limit(5).toPandas()

# %%
df_DFP_Y_complete.where((F.col('year') == 3) & (F.col('Z_DGP_1') == 0)).limit(5).toPandas()

# %%
df_DFP_Y_complete.where((F.col('year') == 3) & (F.col('Z_DGP_1') == 1)).limit(5).toPandas()

# %%
df_DFP_Y_complete.where((F.col('year') == 4) & (F.col('Z_DGP_1') == 0)).limit(5).toPandas()

# %%
df_DFP_Y_complete.where((F.col('year') == 4) & (F.col('Z_DGP_1') == 1)).limit(5).toPandas()

# %% [markdown]
# # Write to Snowflake

# %%
sf_write_spark_df_to_snowflake_new_table(df_DFP_Y_complete, 'DFP_Y')

# %% [markdown]
# # Write to Parquet

# %%
df_DFP_Y_complete.write.parquet('s3a://acic-causality-challenge-2022/DGP/DFP_Y', mode='overwrite')

# %% [markdown]
# # Convert to Original Format [DEPRECATED]

# %% [markdown]
# ## Put it all together

# %%
# df_practice_year_with_DGPs = df_practice_year.join(df_DFP_Z_complete, Z_join_cols, 'left')
# df_practice_year_with_DGPs.persist();
# df_practice_year_with_DGPs.count()

# %%
# df_practice_year_with_DGPs.printSchema()

# %%
# df_patient_year_with_DGPs = df_patient_year.join(df_DFP_Y_complete, Y_join_cols, 'left')
# df_patient_year_with_DGPs.persist();
# df_patient_year_with_DGPs.count()

# %%
# df_patient_year_with_DGPs.printSchema()

# %% [markdown]
# Some of the patients in df_patient_year were not simulated, as they didn't have any pretreatment years. Similarly, some of our simulated patient's years didn't join to df_patient_year, as the patient could be missing year 1 and we used year 2 to start the simulation instead.

# %%
# df_patient_year.count()

# %%
# df_DFP_Y_complete.count()

# %%
# df_patient_year_with_DGPs.count()

# %% [markdown]
# ## Write to Parquet

# %%
# df_practice_year_with_DGPs.write.parquet('s3a://acic-causality-challenge-2022/DGP/practice_year_with_DGPs', mode='overwrite')

# %%
# df_patient_year_with_DGPs.write.parquet('s3a://acic-causality-challenge-2022/DGP/patient_year_with_DGPs', mode='overwrite')

# %% [markdown]
# ## Write to CSV

# %%
# # has ugly csv names, but only one file / dir per dataset_num
# df_practice_year_with_DGPs.repartition(3400, 'dataset_num').write.partitionBy('dataset_num').csv('s3a://acic-causality-challenge-2022/DGP/csv/', mode='overwrite', header=True)

# # Would like to write to efs where it's easier to rename files, but there is an error
# df_practice_year_with_DGPs.repartition(3400, 'dataset_num').write.partitionBy('dataset_num').csv('/efs/mepland/acic_DGP_data/csv/practice_year', mode='overwrite', header=True)
