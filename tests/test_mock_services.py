"""
MockServiceContainerとモックサービスのテスト
"""
import pytest
import json

from core.mock_services import (
    MockDatabaseManager,
    MockAPIClient,
    MockPromptResolver,
    MockServiceContainer
)


class TestMockDatabaseManager:
    """MockDatabaseManagerのテストケース"""
    
    def test_create_and_complete_job(self):
        """ジョブの作成と完了のテスト"""
        db = MockDatabaseManager()
        
        # ジョブ作成
        job_id = db.create_job("test_job", {"test": "config"})
        assert job_id == 1
        assert job_id in db.jobs
        assert db.jobs[job_id]['name'] == "test_job"
        assert db.jobs[job_id]['status'] == 'running'
        
        # ジョブ完了
        db.complete_job(job_id)
        assert db.jobs[job_id]['status'] == 'completed'
    
    def test_create_and_update_image_record(self):
        """画像レコードの作成と更新のテスト"""
        db = MockDatabaseManager()
        
        # 前提として先にジョブを作成
        job_id = db.create_job("test_job", {})
        
        # 画像レコード作成
        workflow = {"test": "workflow"}
        image_id = db.create_image_record(job_id, workflow)
        
        assert image_id == 1
        assert image_id in db.images
        assert db.images[image_id]['job_id'] == job_id
        assert db.images[image_id]['status'] == 'pending'
        assert db.images[image_id]['filepath'] is None
        
        # 画像レコード更新
        db.update_image_record(image_id, "test/path.png", "success")
        assert db.images[image_id]['filepath'] == "test/path.png"
        assert db.images[image_id]['status'] == "success"
    
    def test_get_images_by_job_id(self):
        """ジョブIDによる画像取得のテスト"""
        db = MockDatabaseManager()
        
        # 2つのジョブを作成
        job_id_1 = db.create_job("job1", {})
        job_id_2 = db.create_job("job2", {})
        
        # 各ジョブに画像を作成
        image_id_1 = db.create_image_record(job_id_1, {})
        image_id_2 = db.create_image_record(job_id_2, {})
        image_id_3 = db.create_image_record(job_id_1, {})
        
        # 成功した画像のみ更新
        db.update_image_record(image_id_1, "path1.png", "success")
        db.update_image_record(image_id_2, "path2.png", "success")
        # image_id_3 は pending のまま
        
        # job_id_1 の成功した画像のみ取得されることを確認
        images = db.get_images_by_job_id(job_id_1)
        assert len(images) == 1
        assert images[0]['id'] == image_id_1
    
    def test_sequential_id_assignment(self):
        """IDの連番割り当てのテスト"""
        db = MockDatabaseManager()
        
        # 複数のジョブと画像を作成
        job_id_1 = db.create_job("job1", {})
        job_id_2 = db.create_job("job2", {})
        
        assert job_id_1 == 1
        assert job_id_2 == 2
        
        image_id_1 = db.create_image_record(job_id_1, {})
        image_id_2 = db.create_image_record(job_id_1, {})
        
        assert image_id_1 == 1
        assert image_id_2 == 2


class TestMockAPIClient:
    """MockAPIClientのテストケース"""
    
    def test_queue_prompt(self):
        """プロンプトのキューイングテスト"""
        api = MockAPIClient()
        
        workflow = {"test": "workflow"}
        prompt_id = api.queue_prompt(workflow)
        
        assert prompt_id.startswith("mock_prompt_")
        assert "1" in prompt_id
    
    def test_wait_for_completion(self):
        """完了待機のテスト（モックなので即座に完了）"""
        api = MockAPIClient()
        
        # 例外が発生しないことを確認
        api.wait_for_completion("test_prompt_id")
    
    def test_get_generated_image(self):
        """生成画像取得のテスト"""
        api = MockAPIClient()
        
        result = api.get_generated_image("test_prompt_id")
        assert result is not None
        
        filename, image_data = result
        assert filename.startswith("mock_image_")
        assert image_data == b"FAKE_PNG_DATA"
    
    def test_sequential_prompt_ids(self):
        """連番のプロンプトIDが生成されることのテスト"""
        api = MockAPIClient()
        
        prompt_id_1 = api.queue_prompt({})
        prompt_id_2 = api.queue_prompt({})
        
        assert "1" in prompt_id_1
        assert "2" in prompt_id_2
        assert prompt_id_1 != prompt_id_2


class TestMockPromptResolver:
    """MockPromptResolverのテストケース"""
    
    def test_resolve(self):
        """プロンプト解決のテスト"""
        resolver = MockPromptResolver()
        
        template = "test template with placeholders"
        resolved = resolver.resolve(template)
        
        assert resolved.startswith("[MOCK_RESOLVED]")
        assert template in resolved


class TestMockServiceContainer:
    """MockServiceContainerのテストケース"""
    
    def test_service_container_initialization(self):
        """サービスコンテナの初期化テスト"""
        container = MockServiceContainer()
        
        # 各サービスが正しく初期化されることを確認
        db = container.get_database_manager()
        api = container.get_api_client()
        resolver = container.get_prompt_resolver()
        
        assert isinstance(db, MockDatabaseManager)
        assert isinstance(api, MockAPIClient)
        assert isinstance(resolver, MockPromptResolver)
    
    def test_service_singleton_behavior(self):
        """サービスのシングルトン動作テスト"""
        container = MockServiceContainer()
        
        # 同じインスタンスが返されることを確認
        db1 = container.get_database_manager()
        db2 = container.get_database_manager()
        assert db1 is db2
        
        api1 = container.get_api_client()
        api2 = container.get_api_client()
        assert api1 is api2
        
        resolver1 = container.get_prompt_resolver()
        resolver2 = container.get_prompt_resolver()
        assert resolver1 is resolver2 