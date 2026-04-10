"""
generate_sis_data.py
====================
ETL Pipeline cho nguồn SIS_DB (Student Information System).
Sinh dữ liệu tổng hợp có tương quan với LMS_DB, sau đó load vào admin.duckdb.

Chạy SAU etl_data.py để có danh sách id_student từ academic.duckdb.
"""

import pandas as pd
import numpy as np
import duckdb
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SEED = 42
rng = np.random.default_rng(SEED)

LMS_DB     = "data/lms_db.duckdb"
OUTPUT_DIR = "data"


def load_student_ids() -> pd.DataFrame:
    """Đọc danh sách sinh viên và risk_label từ academic.duckdb."""
    conn = duckdb.connect(LMS_DB, read_only=True)
    df = conn.execute("SELECT id_student, risk_label, imd_band FROM students").df()
    conn.close()
    logging.info(f"Tải được {len(df)} sinh viên từ lms_db.duckdb")
    return df


def generate_billing(students: pd.DataFrame) -> pd.DataFrame:
    """
    Sinh bảng tài chính học phí (SIS: billing).
    Tương quan: High risk → xác suất overdue cao, nợ nhiều hơn.
    """
    logging.info("Sinh billing.csv...")

    debt_prob   = {'High': 0.72, 'Medium': 0.40, 'Low': 0.08}
    scholarship = {'High': 0.15, 'Medium': 0.20, 'Low': 0.12}

    records = []
    for _, row in students.iterrows():
        p  = debt_prob[row['risk_label']]
        overdue = bool(rng.random() < p)
        total_due = round(float(rng.triangular(500, 2500, 8000)), 2) if overdue else 0.0
        amount_paid = round(total_due * float(rng.uniform(0, 0.6)), 2) if overdue else 0.0

        has_scholarship = bool(rng.random() < scholarship[row['risk_label']])
        scholarship_type = rng.choice(
            ['Merit-based', 'Need-based', 'Government grant', None],
            p=[0.3, 0.4, 0.2, 0.1]
        ) if has_scholarship else None

        records.append({
            'student_id':       row['id_student'],
            'total_due':        total_due,
            'amount_paid':      amount_paid,
            'overdue':          overdue,
            'scholarship_type': scholarship_type,
        })

    return pd.DataFrame(records)


def generate_enrollment(students: pd.DataFrame) -> pd.DataFrame:
    """
    Sinh bảng đăng ký học vụ (SIS: enrollment).
    Tương quan: High risk → hay xin bảo lưu, số môn đăng ký ít hơn.
    """
    logging.info("Sinh enrollment.csv...")

    statuses = {
        'High':   (['Enrolled', 'On-Leave', 'Withdrawn'], [0.55, 0.30, 0.15]),
        'Medium': (['Enrolled', 'On-Leave', 'Withdrawn'], [0.80, 0.15, 0.05]),
        'Low':    (['Enrolled', 'On-Leave', 'Withdrawn'], [0.95, 0.04, 0.01]),
    }

    # Ngày nhập học ngẫu nhiên trong 4 năm gần đây
    base_date = pd.Timestamp('2021-09-01')

    records = []
    for _, row in students.iterrows():
        opts, probs = statuses[row['risk_label']]
        status = str(rng.choice(opts, p=probs))

        # Số môn đăng ký: High risk thường đăng ký ít hơn hoặc rút bớt
        num_courses = int(rng.integers(1, 4) if row['risk_label'] == 'High' else rng.integers(3, 7))

        days_offset = int(rng.integers(0, 365 * 4))
        enroll_date = (base_date + pd.Timedelta(days=days_offset)).strftime('%Y-%m-%d')

        records.append({
            'student_id':   row['id_student'],
            'enroll_date':  enroll_date,
            'status':       status,
            'num_courses':  num_courses,
        })

    return pd.DataFrame(records)


def generate_student_profile(students: pd.DataFrame) -> pd.DataFrame:
    """
    Sinh bảng hồ sơ cá nhân (SIS: student_profile).
    Phản ánh yếu tố xã hội: có đi làm thêm, thành phố/tỉnh, liên lạc.
    """
    logging.info("Sinh student_profile.csv...")

    # Sinh viên khó khăn (IMD thấp) có xác suất đi làm thêm cao hơn
    hometowns = [
        'Hà Nội', 'TP. Hồ Chí Minh', 'Đà Nẵng', 'Cần Thơ',
        'Hải Phòng', 'Huế', 'Nha Trang', 'Buôn Ma Thuột',
        'Vinh', 'Thái Nguyên', 'Quy Nhon', 'Vũng Tàu',
    ]

    records = []
    for _, row in students.iterrows():
        # Sinh viên vùng khó khăn (IMD Band thấp) đi làm thêm nhiều hơn
        imd = str(row.get('imd_band', ''))
        p_job = 0.70 if ("0-10%" in imd or "10-20" in imd) else 0.30
        has_part_time_job = bool(rng.random() < p_job)

        # Số điện thoại Việt Nam giả
        phone = f"0{rng.integers(300000000, 999999999)}"

        records.append({
            'student_id':       row['id_student'],
            'phone':            str(phone),
            'email':            f"sv{row['id_student']}@university.edu.vn",
            'hometown':         str(rng.choice(hometowns)),
            'has_part_time_job': has_part_time_job,
        })

    return pd.DataFrame(records)


def load_to_duckdb(billing_df: pd.DataFrame, enroll_df: pd.DataFrame,
                   profile_df: pd.DataFrame, db_path: str):
    """Load 3 bảng SIS vào admin.duckdb."""
    logging.info(f"Ghi vào {db_path}...")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = duckdb.connect(db_path)
    conn.execute("CREATE TABLE billing          AS SELECT * FROM billing_df")
    conn.execute("CREATE TABLE enrollment       AS SELECT * FROM enroll_df")
    conn.execute("CREATE TABLE student_profile  AS SELECT * FROM profile_df")
    conn.close()

    logging.info(f"Hoàn tất SIS ETL → {db_path}")
    logging.info("Các bảng đã tạo: billing, enrollment, student_profile")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Tải danh sách sinh viên từ LMS DB
    students = load_student_ids()

    # 2. Sinh 3 bảng SIS
    billing_df  = generate_billing(students)
    enroll_df   = generate_enrollment(students)
    profile_df  = generate_student_profile(students)

    # 3. ETL → sis_db.duckdb
    load_to_duckdb(billing_df, enroll_df, profile_df, db_path="data/sis_db.duckdb")

    print("\n=== SIS Data Summary ===")
    print(f"Billing:  {billing_df['overdue'].sum()} sinh viên overdue "
          f"({billing_df['overdue'].mean()*100:.1f}%)")
    print(f"Enroll:   {enroll_df['status'].value_counts().to_dict()}")
    print(f"Profile:  {profile_df['has_part_time_job'].sum()} sinh viên đi làm thêm "
          f"({profile_df['has_part_time_job'].mean()*100:.1f}%)")
