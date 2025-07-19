"""
Unit tests for orchestra.py
"""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, MagicMock

from orchestra import Orchestra
from mode_executors import RepoConfig


class TestOrchestra:
    """Test Orchestra main class."""
    
    def test_init_default_config_path(self):
        with patch('orchestra.Orchestra._load_repo_config'), \
             patch('orchestra.Orchestra._load_settings'), \
             patch('orchestra.UsageTracker'):
            
            orchestra = Orchestra()
            expected_path = os.path.join(os.path.dirname(os.path.abspath('orchestra.py')), "config")
            # Check if the path ends with config since absolute paths may vary
            assert orchestra.config_path.endswith("config")
    
    def test_init_custom_config_path(self):
        custom_path = "/custom/config/path"
        
        with patch('orchestra.Orchestra._load_repo_config'), \
             patch('orchestra.Orchestra._load_settings'), \
             patch('orchestra.UsageTracker'):
            
            orchestra = Orchestra(config_path=custom_path)
            assert orchestra.config_path == custom_path
    
    def test_load_repo_config_file_not_found(self, temp_dir):
        config_path = temp_dir
        
        with patch('orchestra.Orchestra._load_settings'), \
             patch('orchestra.UsageTracker'):
            
            orchestra = Orchestra(config_path=config_path)
            assert orchestra.repos == []
    
    def test_load_repo_config_success(self, config_dir):
        with patch('orchestra.Orchestra._load_settings'), \
             patch('orchestra.UsageTracker'):
            
            orchestra = Orchestra(config_path=config_dir)
            
            assert len(orchestra.repos) == 3
            assert orchestra.repos[0].name == "test-repo-1"
            assert orchestra.repos[0].priority == "high"
            assert orchestra.repos[0].watch_branches == ["main", "develop"]
    
    def test_load_repo_config_malformed_yaml(self, temp_dir):
        config_path = Path(temp_dir)
        repos_file = config_path / "repos.yaml"
        
        # Write malformed YAML
        with open(repos_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with patch('orchestra.Orchestra._load_settings'), \
             patch('orchestra.UsageTracker'):
            
            orchestra = Orchestra(config_path=str(config_path))
            assert orchestra.repos == []
    
    def test_load_settings_file_not_found(self, temp_dir):
        config_path = temp_dir
        
        with patch('orchestra.Orchestra._load_repo_config'), \
             patch('orchestra.UsageTracker'):
            
            orchestra = Orchestra(config_path=config_path)
            
            # Should use default settings
            assert orchestra.settings['max_daily_tokens'] == 800000
            assert orchestra.settings['max_daily_requests'] == 8000
            assert orchestra.settings['claude_code_enabled'] == True
    
    def test_load_settings_success(self, config_dir):
        with patch('orchestra.Orchestra._load_repo_config'), \
             patch('orchestra.UsageTracker'):
            
            orchestra = Orchestra(config_path=config_dir)
            
            assert orchestra.settings['max_daily_tokens'] == 100000
            assert orchestra.settings['max_daily_requests'] == 1000
            assert orchestra.settings['workday_max_repos'] == 2
    
    def test_load_settings_malformed_yaml(self, temp_dir):
        config_path = Path(temp_dir)
        settings_file = config_path / "settings.yaml"
        
        # Write malformed YAML
        with open(settings_file, 'w') as f:
            f.write("invalid: yaml: [content")
        
        with patch('orchestra.Orchestra._load_repo_config'), \
             patch('orchestra.UsageTracker'):
            
            orchestra = Orchestra(config_path=str(config_path))
            
            # Should use default settings
            assert orchestra.settings['max_daily_tokens'] == 800000


class TestOrchestraCycle:
    """Test Orchestra cycle execution."""
    
    @pytest.fixture
    def mock_orchestra(self, config_dir):
        with patch('orchestra.UsageTracker') as mock_tracker_class:
            mock_tracker = Mock()
            mock_tracker_class.return_value = mock_tracker
            
            orchestra = Orchestra(config_path=config_dir)
            orchestra.usage_tracker = mock_tracker
            
            return orchestra, mock_tracker
    
    @patch('orchestra.should_run_automation')
    def test_run_cycle_outside_work_hours(self, mock_should_run, mock_orchestra):
        orchestra, mock_tracker = mock_orchestra
        mock_should_run.return_value = False
        
        result = orchestra.run_cycle()
        
        assert result["status"] == "skipped"
        assert result["reason"] == "outside_work_hours"
        assert "timestamp" in result
    
    @patch('orchestra.should_run_automation')
    def test_run_cycle_usage_limit_reached(self, mock_should_run, mock_orchestra):
        orchestra, mock_tracker = mock_orchestra
        mock_should_run.return_value = True
        mock_tracker.check_limits.return_value = "limit_reached"
        mock_tracker.get_usage_summary.return_value = {"total_tokens": 800000, "requests": 8000}
        
        result = orchestra.run_cycle()
        
        assert result["status"] == "skipped"
        assert result["reason"] == "usage_limit_reached"
        assert "usage_summary" in result
    
    @patch('orchestra.should_run_automation')
    @patch('orchestra.get_work_mode')
    def test_run_cycle_off_hours(self, mock_get_mode, mock_should_run, mock_orchestra):
        orchestra, mock_tracker = mock_orchestra
        mock_should_run.return_value = True
        mock_tracker.check_limits.return_value = "normal"
        mock_get_mode.return_value = "off"
        
        result = orchestra.run_cycle()
        
        assert result["status"] == "skipped"
        assert result["reason"] == "off_hours"
    
    @patch('orchestra.should_run_automation')
    @patch('orchestra.get_work_mode')
    @patch('orchestra.get_executor')
    def test_run_cycle_success_no_claude(self, mock_get_executor, mock_get_mode, mock_should_run, mock_orchestra):
        orchestra, mock_tracker = mock_orchestra
        mock_should_run.return_value = True
        mock_tracker.check_limits.return_value = "normal"
        mock_get_mode.return_value = "workday"
        
        # Mock executor
        mock_executor = Mock()
        mock_executor.execute.return_value = {"status": "completed", "results": {}}
        mock_get_executor.return_value = mock_executor
        
        # Disable Claude Code
        orchestra.settings['claude_code_enabled'] = False
        
        result = orchestra.run_cycle()
        
        assert result["status"] == "completed"
        assert result["work_mode"] == "workday"
        assert "execution_result" in result
        assert "duration_seconds" in result
    
    @patch('orchestra.should_run_automation')
    @patch('orchestra.get_work_mode') 
    @patch('orchestra.get_executor')
    def test_run_cycle_executor_exception(self, mock_get_executor, mock_get_mode, mock_should_run, mock_orchestra):
        orchestra, mock_tracker = mock_orchestra
        mock_should_run.return_value = True
        mock_tracker.check_limits.return_value = "normal"
        mock_get_mode.return_value = "workday"
        
        # Mock executor that raises exception
        mock_get_executor.side_effect = Exception("Executor error")
        
        result = orchestra.run_cycle()
        
        assert result["status"] == "error"
        assert result["error"] == "Executor error"
        assert result["work_mode"] == "workday"


class TestOrchestraClaudeIntegration:
    """Test Orchestra Claude Code integration."""
    
    @pytest.fixture
    def mock_orchestra_with_repos(self, config_dir):
        with patch('orchestra.UsageTracker') as mock_tracker_class:
            mock_tracker = Mock()
            mock_tracker_class.return_value = mock_tracker
            
            orchestra = Orchestra(config_path=config_dir)
            orchestra.usage_tracker = mock_tracker
            
            # Mock repos to match config
            orchestra.repos = [
                RepoConfig("test-repo-1", "/tmp/test-repo-1", "high", ["main"]),
                RepoConfig("test-repo-2", "/tmp/test-repo-2", "medium", ["main"])
            ]
            
            return orchestra, mock_tracker
    
    @patch('orchestra.claude_code')
    def test_process_workday_with_claude(self, mock_claude_code, mock_orchestra_with_repos):
        orchestra, mock_tracker = mock_orchestra_with_repos
        mock_claude_code.return_value = "Claude response"
        
        execution_result = {
            "status": "completed",
            "results": {
                "test-repo-1": {
                    "status": "ready",
                    "tasks": [
                        {"type": "review_responses", "prompt": "Review this PR"}
                    ]
                }
            }
        }
        
        result = orchestra._process_workday_with_claude(execution_result)
        
        assert "test-repo-1_review_responses" in result
        assert result["test-repo-1_review_responses"]["status"] == "completed"
        assert result["test-repo-1_review_responses"]["response"] == "Claude response"
        
        mock_claude_code.assert_called_once_with("Review this PR", cwd="/tmp/test-repo-1")
    
    @patch('orchestra.claude_code')
    def test_process_workday_with_claude_error(self, mock_claude_code, mock_orchestra_with_repos):
        orchestra, mock_tracker = mock_orchestra_with_repos
        mock_claude_code.side_effect = Exception("Claude API error")
        
        execution_result = {
            "status": "completed",
            "results": {
                "test-repo-1": {
                    "status": "ready",
                    "tasks": [
                        {"type": "review_responses", "prompt": "Review this PR"}
                    ]
                }
            }
        }
        
        result = orchestra._process_workday_with_claude(execution_result)
        
        assert "test-repo-1_review_responses" in result
        assert result["test-repo-1_review_responses"]["status"] == "error"
        assert "Claude API error" in result["test-repo-1_review_responses"]["error"]
    
    @patch('orchestra.claude_code')
    def test_process_worknight_with_claude(self, mock_claude_code, mock_orchestra_with_repos):
        orchestra, mock_tracker = mock_orchestra_with_repos
        mock_claude_code.return_value = "Claude worknight response"
        
        execution_result = {
            "status": "completed",
            "results": {
                "test-repo-1": {
                    "status": "ready",
                    "prompt": "Worknight development tasks",
                    "mode": "worknight"
                }
            }
        }
        
        result = orchestra._process_worknight_with_claude(execution_result)
        
        assert "test-repo-1" in result
        assert result["test-repo-1"]["status"] == "completed"
        assert result["test-repo-1"]["response"] == "Claude worknight response"
        assert result["test-repo-1"]["mode"] == "worknight"
        
        mock_claude_code.assert_called_once_with("Worknight development tasks", cwd="/tmp/test-repo-1")
    
    @patch('orchestra.claude_code')
    def test_process_worknight_with_claude_error(self, mock_claude_code, mock_orchestra_with_repos):
        orchestra, mock_tracker = mock_orchestra_with_repos
        mock_claude_code.side_effect = Exception("Network timeout")
        
        execution_result = {
            "status": "completed",
            "results": {
                "test-repo-1": {
                    "status": "ready",
                    "prompt": "Worknight tasks"
                }
            }
        }
        
        result = orchestra._process_worknight_with_claude(execution_result)
        
        assert "test-repo-1" in result
        assert result["test-repo-1"]["status"] == "error"
        assert "Network timeout" in result["test-repo-1"]["error"]
    
    @patch('orchestra.should_run_automation')
    @patch('orchestra.get_work_mode')
    @patch('orchestra.get_executor')
    @patch('orchestra.claude_code')
    def test_run_cycle_workday_with_claude_integration(self, mock_claude_code, mock_get_executor, 
                                                      mock_get_mode, mock_should_run, mock_orchestra_with_repos):
        orchestra, mock_tracker = mock_orchestra_with_repos
        mock_should_run.return_value = True
        mock_tracker.check_limits.return_value = "normal"
        mock_get_mode.return_value = "workday"
        mock_claude_code.return_value = "Claude response"
        
        # Mock executor
        mock_executor = Mock()
        mock_executor.execute.return_value = {
            "status": "completed",
            "results": {
                "test-repo-1": {
                    "status": "ready",
                    "tasks": [{"type": "review", "prompt": "Test prompt"}]
                }
            }
        }
        mock_get_executor.return_value = mock_executor
        
        result = orchestra.run_cycle()
        
        assert result["status"] == "completed"
        assert result["work_mode"] == "workday"
        assert "claude_results" in result["execution_result"]
        mock_claude_code.assert_called()
    
    @patch('orchestra.should_run_automation')
    @patch('orchestra.get_work_mode')
    @patch('orchestra.get_executor')
    @patch('orchestra.claude_code')
    def test_run_cycle_worknight_with_claude_integration(self, mock_claude_code, mock_get_executor,
                                                        mock_get_mode, mock_should_run, mock_orchestra_with_repos):
        orchestra, mock_tracker = mock_orchestra_with_repos
        mock_should_run.return_value = True
        mock_tracker.check_limits.return_value = "normal"
        mock_get_mode.return_value = "worknight"
        mock_claude_code.return_value = "Claude worknight response"
        
        # Mock executor
        mock_executor = Mock()
        mock_executor.execute.return_value = {
            "status": "completed",
            "results": {
                "test-repo-1": {
                    "status": "ready",
                    "prompt": "Worknight prompt"
                }
            }
        }
        mock_get_executor.return_value = mock_executor
        
        result = orchestra.run_cycle()
        
        assert result["status"] == "completed"
        assert result["work_mode"] == "worknight"
        assert "claude_results" in result["execution_result"]
        mock_claude_code.assert_called()


class TestOrchestraDaemonMode:
    """Test Orchestra daemon mode functionality."""
    
    @pytest.fixture
    def mock_orchestra_daemon(self, config_dir):
        with patch('orchestra.UsageTracker') as mock_tracker_class:
            mock_tracker = Mock()
            mock_tracker_class.return_value = mock_tracker
            
            orchestra = Orchestra(config_path=config_dir)
            orchestra.usage_tracker = mock_tracker
            
            return orchestra, mock_tracker
    
    @patch('orchestra.time.sleep')
    def test_run_daemon_single_cycle(self, mock_sleep, mock_orchestra_daemon):
        orchestra, mock_tracker = mock_orchestra_daemon
        
        # Mock run_cycle to stop after first iteration
        with patch.object(orchestra, 'run_cycle') as mock_run_cycle:
            mock_run_cycle.return_value = {"status": "completed", "usage_status": "normal"}
            
            # Mock KeyboardInterrupt to stop daemon
            mock_sleep.side_effect = KeyboardInterrupt()
            
            orchestra.run_daemon()
            
            mock_run_cycle.assert_called_once()
            mock_sleep.assert_called_once()
    
    def test_run_once(self, mock_orchestra_daemon):
        orchestra, mock_tracker = mock_orchestra_daemon
        
        with patch.object(orchestra, 'run_cycle') as mock_run_cycle:
            mock_run_cycle.return_value = {"status": "completed"}
            
            result = orchestra.run_once()
            
            assert result["status"] == "completed"
            mock_run_cycle.assert_called_once()


class TestOrchestraMain:
    """Test Orchestra main function and argument parsing."""
    
    @patch('orchestra.Orchestra')
    def test_main_run_once(self, mock_orchestra_class):
        mock_orchestra = Mock()
        mock_orchestra_class.return_value = mock_orchestra
        
        with patch('sys.argv', ['orchestra.py', '--run-once']):
            from orchestra import main
            main()
            
            mock_orchestra.run_once.assert_called_once()
    
    @patch('orchestra.Orchestra')
    def test_main_daemon_mode(self, mock_orchestra_class):
        mock_orchestra = Mock()
        mock_orchestra_class.return_value = mock_orchestra
        
        with patch('sys.argv', ['orchestra.py', '--daemon']):
            from orchestra import main
            main()
            
            mock_orchestra.run_daemon.assert_called_once()
    
    @patch('orchestra.Orchestra')
    def test_main_test_mode(self, mock_orchestra_class):
        mock_orchestra = Mock()
        mock_orchestra.settings = {'claude_code_enabled': True}
        mock_orchestra_class.return_value = mock_orchestra
        
        with patch('sys.argv', ['orchestra.py', '--test-mode', '--run-once']):
            from orchestra import main
            main()
            
            # Should disable Claude Code in test mode
            assert mock_orchestra.settings['claude_code_enabled'] == False
            mock_orchestra.run_once.assert_called_once()
    
    @patch('orchestra.Orchestra')
    def test_main_custom_config(self, mock_orchestra_class):
        mock_orchestra = Mock()
        mock_orchestra_class.return_value = mock_orchestra
        
        with patch('sys.argv', ['orchestra.py', '--config', '/custom/config', '--run-once']):
            from orchestra import main
            main()
            
            mock_orchestra_class.assert_called_once_with(config_path='/custom/config')
            mock_orchestra.run_once.assert_called_once()
    
    @patch('orchestra.Orchestra')
    def test_main_default_behavior(self, mock_orchestra_class):
        mock_orchestra = Mock()
        mock_orchestra_class.return_value = mock_orchestra
        
        with patch('sys.argv', ['orchestra.py']):
            from orchestra import main
            main()
            
            # Default behavior should be run_once
            mock_orchestra.run_once.assert_called_once()


class TestOrchestraEdgeCases:
    """Test Orchestra edge cases and error scenarios."""
    
    def test_process_workday_skip_non_ready_repos(self, config_dir):
        with patch('orchestra.UsageTracker'):
            orchestra = Orchestra(config_path=config_dir)
            
            execution_result = {
                "status": "completed",
                "results": {
                    "ready-repo": {
                        "status": "ready",
                        "tasks": [{"type": "review", "prompt": "Test"}]
                    },
                    "error-repo": {
                        "status": "error",
                        "error": "Some error"
                    },
                    "skipped-repo": {
                        "status": "skipped"
                    }
                }
            }
            
            with patch('orchestra.claude_code') as mock_claude_code:
                mock_claude_code.return_value = "Response"
                
                # Mock finding the repo config
                orchestra.repos = [RepoConfig("ready-repo", "/tmp/ready", "high", ["main"])]
                
                result = orchestra._process_workday_with_claude(execution_result)
                
                # Should only process the ready repo
                assert len(result) == 1
                assert "ready-repo_review" in result
    
    def test_process_worknight_skip_non_ready_repos(self, config_dir):
        with patch('orchestra.UsageTracker'):
            orchestra = Orchestra(config_path=config_dir)
            
            execution_result = {
                "status": "completed",
                "results": {
                    "ready-repo": {
                        "status": "ready",
                        "prompt": "Worknight tasks"
                    },
                    "error-repo": {
                        "status": "error"
                    }
                }
            }
            
            with patch('orchestra.claude_code') as mock_claude_code:
                mock_claude_code.return_value = "Response"
                
                orchestra.repos = [RepoConfig("ready-repo", "/tmp/ready", "high", ["main"])]
                
                result = orchestra._process_worknight_with_claude(execution_result)
                
                # Should only process the ready repo
                assert len(result) == 1
                assert "ready-repo" in result
    
    def test_repo_config_not_found_in_claude_processing(self, config_dir):
        with patch('orchestra.UsageTracker'):
            orchestra = Orchestra(config_path=config_dir)
            orchestra.repos = []  # Empty repos list
            
            execution_result = {
                "status": "completed",
                "results": {
                    "unknown-repo": {
                        "status": "ready",
                        "tasks": [{"type": "review", "prompt": "Test"}]
                    }
                }
            }
            
            with patch('orchestra.claude_code'):
                result = orchestra._process_workday_with_claude(execution_result)
                
                # Should not process any repos if config not found
                assert len(result) == 0