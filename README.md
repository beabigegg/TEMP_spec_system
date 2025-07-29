# TEMP Spec System - 暫時規範管理系統

這是一個使用 Flask 開發的 Web 應用程式，旨在管理、追蹤和存檔暫時性的工程規範。系統支援完整的生命週期管理，從建立、審核、生效到終止，並能自動生成標準化文件。

## 核心功能

- **使用者權限管理**: 內建三種角色 (`viewer`, `editor`, `admin`)，各角色擁有不同操作權限。
- **規範生命週期**: 支援暫時規範的建立、啟用、展延、終止與刪除。
- **文件自動生成**: 可根據 Word 模板 (`.docx`) 自動填入內容並生成 PDF 與 Word 文件。
- **檔案管理**: 支援上傳簽核後的文件，並與對應的規範進行關聯。
- **歷史紀錄**: 詳細記錄每一份規範的所有變更歷史，方便追蹤與稽核。
- **內容編輯**: 支援 Markdown 語法及圖片上傳，提供豐富的內容編輯體驗。

---

## 環境要求

在部署此應用程式之前，請確保您的系統已安裝以下軟體：

1.  **Python**: 建議使用 `Python 3.10` 或更高版本。
2.  **MySQL**: 需要一個 MySQL 資料庫來儲存所有應用程式資料。
3.  **Microsoft Office / LibreOffice**:
    - **[重要]** 本專案使用 `docx2pdf` 套件來將 Word 文件轉換為 PDF。此套件依賴於系統上安裝的 Microsoft Office (Windows) 或 LibreOffice (跨平台)。請務必確保伺服器上已安裝其中之一，否則 PDF 生成功能將會失敗。
4.  **Git**: 用於從版本控制系統下載程式碼。

---

## 安裝與設定步驟

請依照以下步驟來設定您的開發或生產環境：

### 1. 下載程式碼

```bash
git clone <your-repository-url>
cd TEMP_spec_system
```

### 2. 建立並啟用虛擬環境

建議使用虛擬環境來隔離專案的相依套件。

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 4. 設定環境變數

專案的敏感設定（如資料庫連線資訊、密鑰）是透過 `.env` 檔案管理的。

首先，複製範例檔案：

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

然後，編輯 `.env` 檔案，填入您的實際設定：

```dotenv
# Flask 應用程式的密鑰，用於保護 session，請務必修改為一個隨機的長字串
SECRET_KEY='your-super-secret-and-random-string'

# 資料庫連線 URL
# 格式: mysql+pymysql://<使用者名稱>:<密碼>@<主機地址>:<埠號>/<資料庫名稱>
DATABASE_URL='mysql+pymysql://user:password@localhost:3306/temp_spec_db'
```

**注意**: 請先在您的 MySQL 中手動建立一個名為 `temp_spec_db` (或您自訂的名稱) 的資料庫。

### 5. 初始化資料庫

執行初始化腳本來建立所有需要的資料表，並產生一個預設的管理員帳號。

```bash
python init_db.py
```

腳本會提示您確認操作。輸入 `yes` 後，它會建立資料表並在終端機中顯示預設 `admin` 帳號的隨機密碼。**請務必記下此密碼**。

---

## 執行應用程式

### 開發模式

在開發環境中，您可以直接執行 `app.py`：

```bash
python app.py
```

應用程式預設會在 `http://127.0.0.1:5000` 上執行。

### 生產環境

在生產環境中，**不應**使用 Flask 內建的開發伺服器。建議使用生產級的 WSGI 伺服器，例如 `Gunicorn` (Linux) 或 `Waitress` (Windows)。

**使用 Waitress (Windows) 的範例:**

1.  安裝 Waitress: `pip install waitress`
2.  執行應用程式: `waitress-serve --host=0.0.0.0 --port=8000 app:app`

---

## 使用者角色說明

- **Viewer (檢視者)**:
  - 只能瀏覽和搜尋暫時規範。
  - 可以下載已生效或待生效的 PDF 文件。
- **Editor (編輯者)**:
  - 擁有 `Viewer` 的所有權限。
  - 可以建立新的暫時規範，並下載待簽核的 Word 文件。
  - 可以展延或終止已生效的規範。
- **Admin (管理者)**:
  - 擁有 `Editor` 的所有權限。
  - 可以管理使用者帳號 (新增、編輯、刪除)。
  - **可以上傳簽核後的文件，正式啟用一份規範**。
  - 可以永久刪除一份規範及其所有相關檔案。
