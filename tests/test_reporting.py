"""
Reportingモジュールのテスト
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from core.reporting.base import JobReportData, ImageData
from core.reporting.html import HTMLReportGenerator
from core.reporting.reporter import Reporter


class TestImageData:
    """ImageDataクラスのテスト"""
    
    def test_image_data_creation(self):
        """ImageDataの作成テスト"""
        image_data = ImageData(
            id=1,
            filepath="results/images/00000001.png",
            variable_value="test value",
            status="success"
        )
        
        assert image_data.id == 1
        assert image_data.filepath == "results/images/00000001.png"
        assert image_data.variable_value == "test value"
        assert image_data.status == "success"
    
    def test_image_data_default_status(self):
        """ImageDataのデフォルトステータステスト"""
        image_data = ImageData(
            id=1,
            filepath="test.png",
            variable_value="test"
        )
        
        assert image_data.status == "success"


class TestJobReportData:
    """JobReportDataクラスのテスト"""
    
    def test_job_report_data_creation(self):
        """JobReportDataの作成テスト"""
        images = [
            ImageData(id=1, filepath="test1.png", variable_value="value1"),
            ImageData(id=2, filepath="test2.png", variable_value="value2")
        ]
        
        variables = [{'node_id': 1, 'input_name': 'text', 'values': ['test']}]
        
        job_data = JobReportData(
            job_id=123,
            job_name="Test Job",
            images=images,
            variables=variables,
            variable_name="text"
        )
        
        assert job_data.job_id == 123
        assert job_data.job_name == "Test Job"
        assert len(job_data.images) == 2
        assert job_data.variables == variables
        assert job_data.variable_name == "text"


class TestHTMLReportGenerator:
    """HTMLReportGeneratorクラスのテスト"""
    
    @pytest.fixture
    def temp_template_dir(self):
        """一時テンプレートディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        template_dir = Path(temp_dir)
        
        # テスト用テンプレートファイルを作成
        template_content = """<!DOCTYPE html>
<html>
<head><title>{{ job_name }}</title></head>
<body>
    <h1>Job: {{ job_name }} (ID: {{ job_id }})</h1>
    <div>
        {% for image in images %}
        <div>
            <img src="{{ image.filepath }}" alt="Image {{ image.id }}">
            <p>{{ variable_name }}: {{ image.variable_value }}</p>
        </div>
        {% endfor %}
    </div>
</body>
</html>"""
        
        with open(template_dir / 'report.html.j2', 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        yield str(template_dir)
        
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir)
    
    def test_html_generator_initialization(self, temp_template_dir):
        """HTMLReportGeneratorの初期化テスト"""
        generator = HTMLReportGenerator(temp_template_dir)
        assert generator.template_dir == temp_template_dir
        assert generator.env is not None
    
    def test_html_report_generation(self, temp_template_dir):
        """HTMLレポート生成テスト"""
        generator = HTMLReportGenerator(temp_template_dir)
        
        # テストデータ準備
        images = [
            ImageData(id=1, filepath="results/images/00000001.png", variable_value="anime"),
            ImageData(id=2, filepath="results/images/00000002.png", variable_value="realistic")
        ]
        
        job_data = JobReportData(
            job_id=123,
            job_name="Test Job",
            images=images,
            variables=[{'node_id': 1, 'input_name': 'style'}],
            variable_name="style"
        )
        
        # 一時出力ファイル
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.html', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            # レポート生成
            generator.generate(job_data, output_path)
            
            # 生成されたファイルの確認
            assert output_path.exists()
            
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 期待される内容が含まれていることを確認
            assert "Test Job" in content
            assert "123" in content
            assert "anime" in content
            assert "realistic" in content
            assert "style" in content
            
        finally:
            # クリーンアップ
            if output_path.exists():
                output_path.unlink()
    
    def test_format_images_for_template(self, temp_template_dir):
        """画像データのテンプレート用変換テスト"""
        generator = HTMLReportGenerator(temp_template_dir)
        
        images = [
            ImageData(id=1, filepath="results/images/test1.png", variable_value="value1"),
            ImageData(id=2, filepath="results/images/test2.png", variable_value="value2")
        ]
        
        formatted = generator._format_images_for_template(images)
        
        assert len(formatted) == 2
        assert formatted[0]['id'] == 1
        assert formatted[0]['filepath'] == "images/test1.png"  # results/ からの相対パス
        assert formatted[0]['variable_value'] == "value1"


class TestReporter:
    """Reporterクラスのテスト"""
    
    @pytest.fixture
    def temp_template_dir(self):
        """一時テンプレートディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        template_dir = Path(temp_dir)
        
        # シンプルなテンプレート
        template_content = """<html><body>{{ job_name }}</body></html>"""
        with open(template_dir / 'report.html.j2', 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        yield str(template_dir)
        
        import shutil
        shutil.rmtree(temp_dir)
    
    def test_reporter_initialization(self, temp_template_dir):
        """Reporterの初期化テスト"""
        reporter = Reporter(temp_template_dir)
        assert reporter.html_generator is not None
    
    def test_convert_image_records(self, temp_template_dir):
        """画像レコード変換テスト"""
        reporter = Reporter(temp_template_dir)
        
        # テスト用のworkflowデータ
        workflow_data = {
            "1": {
                "inputs": {
                    "text": "test prompt"
                }
            }
        }
        
        image_records = [
            {
                'id': 1,
                'filepath': 'results/images/00000001.png',
                'workflow': json.dumps(workflow_data),
                'status': 'success'
            }
        ]
        
        variables = [{'node_id': 1, 'input_name': 'text'}]
        
        images = reporter._convert_image_records(image_records, variables)
        
        assert len(images) == 1
        assert images[0].id == 1
        assert images[0].filepath == 'results/images/00000001.png'
        assert images[0].variable_value == "test prompt"
        assert images[0].status == 'success'
    
    def test_convert_image_records_with_invalid_workflow(self, temp_template_dir):
        """不正なworkflowデータでの画像レコード変換テスト"""
        reporter = Reporter(temp_template_dir)
        
        image_records = [
            {
                'id': 1,
                'filepath': 'test.png',
                'workflow': 'invalid json',
                'status': 'success'
            }
        ]
        
        variables = [{'node_id': 1, 'input_name': 'text'}]
        
        # 不正なJSONでも例外を発生させずに空のリストを返す
        images = reporter._convert_image_records(image_records, variables)
        assert len(images) == 0
    
    def test_convert_image_records_no_variables(self, temp_template_dir):
        """変数なしでの画像レコード変換テスト"""
        reporter = Reporter(temp_template_dir)
        
        image_records = [{'id': 1, 'filepath': 'test.png', 'workflow': '{}'}]
        variables = []
        
        images = reporter._convert_image_records(image_records, variables)
        assert len(images) == 0
    
    @patch('core.reporting.html.HTMLReportGenerator.generate')
    def test_generate_html_report(self, mock_generate, temp_template_dir):
        """HTMLレポート生成のインテグレーションテスト"""
        reporter = Reporter(temp_template_dir)
        
        workflow_data = {"1": {"inputs": {"text": "test prompt"}}}
        image_records = [
            {
                'id': 1,
                'filepath': 'results/images/00000001.png',
                'workflow': json.dumps(workflow_data),
                'status': 'success'
            }
        ]
        
        variables = [{'node_id': 1, 'input_name': 'text'}]
        
        reporter.generate_html_report(
            job_id=123,
            job_name="Test Job",
            image_records=image_records,
            variables=variables
        )
        
        # HTMLReportGenerator.generateが呼ばれたことを確認
        assert mock_generate.called
        args, kwargs = mock_generate.call_args
        job_data = args[0]
        output_path = args[1]
        
        assert job_data.job_id == 123
        assert job_data.job_name == "Test Job"
        assert len(job_data.images) == 1
        assert str(output_path).endswith("report_job_123.html")