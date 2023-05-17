# %% [markdown]
# # Setup

# %%
spark

# %%
# %info

# %%
import pyspark.sql.functions as F
from pyspark.sql.types import IntegerType

# %% [markdown]
# # Load CSVs From s3

# %% [markdown]
# ## `PATIENT`

# %%
df_patient_raw = spark.read.options(header=True).csv('s3a://acic-causality-challenge-2022/patient/')

# %%
df_patient = (df_patient_raw
.withColumn('id_patient', F.col('`id.patient`').cast('int'))
.withColumn('id_practice', F.col('`id.practice`').cast('int'))
.withColumn('V1', F.col('V1').cast('double'))
.withColumn('V2', F.col('V2').cast('int'))
.withColumn('V3', F.col('V3').cast('int'))
.withColumn('V4', F.col('V4').cast('double'))
.withColumn('filename', F.regexp_replace(F.element_at(F.split(F.input_file_name(), '/'), -1), '\.csv', '') )
.withColumn('dataset_num', F.element_at(F.split(F.col('filename'), '_'), -1).cast('int') )
.select(['dataset_num', 'id_patient', 'id_practice', 'V1', 'V2', 'V3', 'V4', 'V5', 'filename'])
)

# %%
df_patient.count()

# %%
df_patient.printSchema()

# %% [markdown]
# ## `PATIENT_YEAR`

# %%
df_patient_year_raw = spark.read.options(header=True).csv('s3a://acic-causality-challenge-2022/patient_year/')

# %%
df_patient_year = (df_patient_year_raw
.withColumn('id_patient', F.col('`id.patient`').cast('int'))
.withColumn('year', F.col('year').cast('int'))
.withColumn('Y', F.col('Y').cast('double'))
.withColumn('filename', F.regexp_replace(F.element_at(F.split(F.input_file_name(), '/'), -1), '\.csv', '') )
.withColumn('dataset_num', F.element_at(F.split(F.col('filename'), '_'), -1).cast('int') )
.select(['dataset_num', 'id_patient', 'year', 'Y', 'filename'])
)

# %%
df_patient_year.count()

# %%
df_patient_year.printSchema()

# %% [markdown]
# ## `PRACTICE`

# %%
df_practice_raw = spark.read.options(header=True).csv('s3a://acic-causality-challenge-2022/practice/')

# %%
df_practice = (df_practice_raw
.withColumn('id_practice', F.col('`id.practice`').cast('int'))
.withColumn('X1', F.col('X1').cast('int'))
.withColumn('X3', F.col('X3').cast('int'))
.withColumn('X5', F.col('X5').cast('int'))
.withColumn('X6', F.col('X6').cast('double'))
.withColumn('X7', F.col('X7').cast('double'))
.withColumn('X8', F.col('X8').cast('double'))
.withColumn('X9', F.col('X9').cast('double'))
.withColumn('filename', F.regexp_replace(F.element_at(F.split(F.input_file_name(), '/'), -1), '\.csv', '') )
.withColumn('dataset_num', F.element_at(F.split(F.col('filename'), '_'), -1).cast('int') )
.select(['dataset_num', 'id_practice', 'X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9', 'filename'])
)

# %%
df_practice.count()

# %%
df_practice.printSchema()

# %% [markdown]
# ## `PRACTICE_YEAR`

# %%
df_practice_year_raw = spark.read.options(header=True).csv('s3a://acic-causality-challenge-2022/practice_year/')

# %%
df_practice_year = (df_practice_year_raw
.withColumn('id_practice', F.col('`id.practice`').cast('int'))
.withColumn('year', F.col('year').cast('int'))
.withColumn('Y', F.col('Y').cast('double'))
.withColumn('Z', F.col('Z').cast('int'))
.withColumn('post', F.col('post').cast('int'))
.withColumn('n_patients', F.col('`n.patients`').cast('int'))
.withColumn('V1_avg', F.col('V1_avg').cast('double'))
.withColumn('V2_avg', F.col('V2_avg').cast('double'))
.withColumn('V3_avg', F.col('V3_avg').cast('double'))
.withColumn('V4_avg', F.col('V4_avg').cast('double'))
.withColumn('V5_A_avg', F.col('V5_A_avg').cast('double'))
.withColumn('V5_B_avg', F.col('V5_B_avg').cast('double'))
.withColumn('V5_C_avg', F.col('V5_C_avg').cast('double'))
.withColumn('filename', F.regexp_replace(F.element_at(F.split(F.input_file_name(), '/'), -1), '\.csv', '') )
.withColumn('dataset_num', F.element_at(F.split(F.col('filename'), '_'), -1).cast('int') )
.select(['dataset_num', 'id_practice', 'year', 'Y', 'Z', 'post', 'n_patients',
         'V1_avg', 'V2_avg', 'V3_avg', 'V4_avg', 'V5_A_avg', 'V5_B_avg', 'V5_C_avg', 'filename'])
)

# %%
df_practice_year.count()

# %%
df_practice_year.printSchema()


# %% [markdown]
# # Encode Tables

# %% [markdown]
# ## Prep One Hot Encoding Code

# %% [raw]
# # Pyspark native one hot encoding pipeline makes hard to read dense vectors
#
# # from pyspark.ml.feature import StringIndexer
# # from pyspark.ml.feature import OneHotEncoder
#
# # def my_one_hot_encoder(df_in, inputCols, output_postfix='_vec'):
# #     index_cols = [f'{col}_index' for col in inputCols]
# #     output_cols = [f'{col}{output_postfix}' for col in inputCols]
#
# #     indexer = StringIndexer(inputCols=inputCols, outputCols=index_cols)
# #     df_indexed = indexer.fit(df_in).transform(df_in)
#
# #     encoder = OneHotEncoder(inputCols=index_cols, outputCols=output_cols, dropLast=False)
# #     df_out = encoder.fit(df_indexed).transform(df_indexed)
#
# #     return df_out

# %%
# Let's do it ourselves in a human readable way
# adapted from https://towardsdev.com/how-to-write-pyspark-one-hot-encoding-results-to-an-interpretable-csv-file-626ecb973962

def my_one_hot_encoder(_df, inputCols, drop_old_cols=False):
    new_cols = []

    def _my_one_hot_encoder_col(_df, inputCol):
        _new_cols = []

        distinct_values = sorted(_df.select(inputCol).distinct().rdd.flatMap(lambda x: x).collect())

        for distinct_value in distinct_values:
            _udf = F.udf(lambda item: 1 if item == distinct_value else 0, IntegerType())

            _new_col = f'{inputCol}_{distinct_value}'
            _new_cols.append(_new_col)

            _df = _df.withColumn(_new_col, _udf(F.col(inputCol)))

        return _df, _new_cols

    for inputCol in inputCols:
        _df, _new_cols = _my_one_hot_encoder_col(_df, inputCol)
        new_cols.extend(_new_cols)

    if drop_old_cols:
        _df = _df.select([col for col in _df.columns if col not in inputCols])

    return _df


# %% [markdown]
# ## Run Encoding

# %%
df_patient_encoded = my_one_hot_encoder(df_patient, inputCols=['V5'])
df_patient_encoded = df_patient_encoded.select(['dataset_num', 'id_patient', 'id_practice',
    'V1', 'V2', 'V3', 'V4', 'V5',
    'V5_A', 'V5_B', 'V5_C',
    'filename'])

# %%
df_practice_encoded = my_one_hot_encoder(df_practice, inputCols=['X2', 'X4'])
df_practice_encoded = df_practice_encoded.select(['dataset_num', 'id_practice',
    'X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9',
    'X2_A', 'X2_B', 'X2_C', 'X4_A', 'X4_B', 'X4_C',
    'filename'])

# %% [markdown]
# ## Save to Parquet

# %%
df_patient_encoded.write.parquet('s3a://acic-causality-challenge-2022/parquet/patient', mode='overwrite')

# %%
df_patient_year.write.parquet('s3a://acic-causality-challenge-2022/parquet/patient_year', mode='overwrite')

# %%
df_practice_encoded.write.parquet('s3a://acic-causality-challenge-2022/parquet/practice', mode='overwrite')

# %%
df_practice_year.write.parquet('s3a://acic-causality-challenge-2022/parquet/practice_year', mode='overwrite')

# %% [markdown]
# # Join Tables

# %% [markdown]
# ## Patient Level

# %%
patient_features = [col for col in df_patient_year.columns + df_patient_encoded.columns
    if col not in ['dataset_num', 'id_practice', 'id_patient', 'year', 'filename']]

# %%
patient_features

# %%
df_patient_joined = (df_patient_year
    .join(df_patient_encoded, ['dataset_num', 'id_patient'], 'left')
    .select(['dataset_num', 'id_practice', 'id_patient', 'year'] + patient_features)
)

# %%
df_patient_joined.persist();

# %%
df_patient_joined.count()

# %%
df_patient_joined.printSchema()

# %% [markdown]
# ## Practice Level

# %%
practice_features = [col for col in df_practice_year.columns + df_practice_encoded.columns
    if col not in ['dataset_num', 'id_practice', 'year', 'Z', 'post', 'filename']]

# %%
practice_features

# %%
df_practice_joined = (df_practice_year
    .join(df_practice_encoded, ['dataset_num', 'id_practice'], 'left')
    .select(['dataset_num', 'id_practice', 'Z', 'post', 'year'] + practice_features)
)

# %%
df_practice_joined.persist();

# %%
df_practice_joined.count()

# %%
df_practice_joined.printSchema()

# %% [markdown]
# ## Save to Parquet

# %%
df_patient_joined.write.parquet('s3a://acic-causality-challenge-2022/patient_joined', mode='overwrite')

# %%
df_practice_joined.write.parquet('s3a://acic-causality-challenge-2022/practice_joined', mode='overwrite')
