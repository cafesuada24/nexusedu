import pandas as pd
import duckdb
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class OuladETLPipeline:
    """
    ETL Pipeline cho nguồn LMS_DB.
    Đọc dữ liệu thô OULAD (CSV) → Aggregate → Lưu vào academic.duckdb.
    """

    def __init__(self, data_dir="data", db_path="data/lms_db.duckdb", module_code="AAA"):
        self.data_dir = data_dir
        self.db_path = db_path
        self.module_code = module_code

    def extract(self) -> tuple:
        logging.info("Đọc dữ liệu OULAD thô (.csv)...")
        try:
            student_info = pd.read_csv(os.path.join(self.data_dir, "studentInfo.csv"))
            vle_logs    = pd.read_csv(os.path.join(self.data_dir, "studentVle.csv"))
            assessments = pd.read_csv(os.path.join(self.data_dir, "studentAssessment.csv"))
            return student_info, vle_logs, assessments
        except FileNotFoundError as e:
            logging.error(f"Không tìm thấy file: {e}")
            raise

    def transform(self, student_info, vle_logs, assessments) -> pd.DataFrame:
        logging.info(f"Lọc môn học: {self.module_code}")
        student_info = student_info[student_info['code_module'] == self.module_code].copy()
        valid_ids = set(student_info['id_student'].unique())
        logging.info(f"Số sinh viên: {len(valid_ids)}")

        # Aggregate VLE clicks
        vle_summary = (vle_logs[vle_logs['id_student'].isin(valid_ids)]
                       .groupby('id_student')['sum_click'].sum().reset_index())

        # Aggregate assessment scores
        score_summary = (assessments[assessments['id_student'].isin(valid_ids)]
                         .groupby('id_student')['score'].mean().reset_index())

        df = student_info.merge(vle_summary, on='id_student', how='left')
        df = df.merge(score_summary, on='id_student', how='left')
        df['sum_click'] = df['sum_click'].fillna(0)
        df['score']     = df['score'].fillna(0)

        # Risk Engine
        df['risk_score'] = df.apply(self._calculate_risk, axis=1)
        df['risk_label'] = df['risk_score'].apply(self._assign_label)

        cols = ['id_student', 'gender', 'region', 'highest_education', 'imd_band',
                'studied_credits', 'sum_click', 'score', 'risk_score', 'risk_label', 'final_result']
        return df[cols]

    def _calculate_risk(self, row) -> int:
        s = 0
        if row['score'] < 30:    s += 40
        elif row['score'] < 50:  s += 20
        if row['sum_click'] < 300:   s += 30
        elif row['sum_click'] < 800: s += 15
        if row['studied_credits'] > 100: s += 15
        elif row['studied_credits'] > 60: s += 5
        if pd.notna(row['imd_band']) and ("0-10%" in row['imd_band'] or "10-20" in row['imd_band']):
            s += 15
        return min(s, 100)

    def _assign_label(self, score) -> str:
        if score >= 60: return 'High'
        if score >= 35: return 'Medium'
        return 'Low'

    def load(self, df: pd.DataFrame):
        logging.info(f"Ghi vào {self.db_path}...")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        conn = duckdb.connect(self.db_path)
        conn.execute("CREATE TABLE students AS SELECT * FROM df")
        conn.close()

        logging.info(f"Hoàn tất: {len(df)} sinh viên → {self.db_path}")
        print(df['risk_label'].value_counts().to_string())

    def run(self):
        raw_info, raw_vle, raw_assessments = self.extract()
        df = self.transform(raw_info, raw_vle, raw_assessments)
        self.load(df)
        return df  # Trả về để generate_sis_data.py dùng lại danh sách ID


if __name__ == "__main__":
    pipeline = OuladETLPipeline(
        data_dir="data",
        db_path="data/lms_db.duckdb",
        module_code="AAA"
    )
    pipeline.run()
