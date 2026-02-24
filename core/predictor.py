"""
核心预测模块
封装 Amazon Chronos-Bolt 模型进行时间序列预测
"""
import os
import torch
import numpy as np
import pandas as pd
from typing import List, Optional, Union
import logging
from transformers import AutoModelForSeq2SeqLM, AutoConfig

# 尝试导入 chronos 库，若未安装则提供友好提示
try:
    from chronos import BaseChronosPipeline
except ImportError:
    BaseChronosPipeline = None

logger = logging.getLogger("core.predictor")

class FinancialPredictor:
    """金融时间序列预测器"""
    
    def __init__(self, model_name: str = "amazon/chronos-bolt-tiny", device: str = None):
        """
        初始化预测器
        
        Args:
            model_name: 模型名称，默认使用 lightest 的 tiny 版本
            device: 运行设备 ('cpu' or 'cuda')，默认自动检测
        """
        self.model_name = model_name
        self.pipeline = None
        
        if device:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
        logger.info(f"FinancialPredictor 初始化 (Device: {self.device})")

    def _load_model(self):
        """延迟加载模型"""
        if self.pipeline is not None:
            return

        if BaseChronosPipeline is None:
            raise ImportError(
                "未找到 chronos-forecasting 库。请运行 `pip install chronos-forecasting` 安装。"
            )

        try:
            logger.info(f"正在加载模型: {self.model_name} ...")
            # 使用 bfloat16 加速推理 (如果硬件支持)
            torch_dtype = torch.bfloat16 if self.device == "cuda" or (self.device == "cpu" and torch.cuda.is_bf16_supported()) else torch.float32
            
            self.pipeline = BaseChronosPipeline.from_pretrained(
                self.model_name,
                device_map=self.device,
                torch_dtype=torch_dtype,
            )
            logger.info("模型加载完成")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise e

    def predict(self, 
                context: Union[List[float], np.ndarray, pd.Series], 
                prediction_length: int = 12, 
                num_samples: int = 20) -> dict:
        """
        执行预测
        
        Args:
            context: 历史数据序列 (一维)
            prediction_length: 预测步长
            num_samples: 采样数量 (注意：Bolt模型实际上使用固定分位数，此参数可能被忽略或有不同含义)
            
        Returns:
            包含预测结果的字典:
            {
                'mean': List[float],    # 均值预测
                'median': List[float],  # 中位数预测
                'lower_80': List[float], # 10% 分位数
                'upper_80': List[float]  # 90% 分位数
            }
        """
        self._load_model()
        
        # 数据预处理
        if isinstance(context, list):
            context_tensor = torch.tensor(context)
        elif isinstance(context, np.ndarray):
            context_tensor = torch.from_numpy(context)
        elif isinstance(context, pd.Series):
            context_tensor = torch.tensor(context.values)
        else:
            raise ValueError("不支持的输入数据类型")
            
        # 确保数据是浮点型
        context_tensor = context_tensor.float()
        
        try:
            # 执行预测
            # Bolt returns quantiles directly: [batch_size, num_quantiles, prediction_length]
            forecast = self.pipeline.predict(
                inputs=context_tensor,  # 使用正确的参数名 inputs
                prediction_length=prediction_length,
                limit_prediction_length=False
            )
            
            # 提取统计特征 (取第一个序列，因为我们输入是单个序列)
            forecast_samples = forecast[0].numpy() # shape: [num_quantiles, prediction_length]
            # Quantiles: 0.1, 0.2, ..., 0.9 (9 quantiles default)
            
            # Mapping quantiles to our expected stats
            median = forecast_samples[4] # 0.5 quantile
            lower_80 = forecast_samples[0] # 0.1 quantile
            upper_80 = forecast_samples[8] # 0.9 quantile
            mean = median # Approximate mean with median for quantile forecasts
            
            return {
                "mean": mean.tolist(),
                "median": median.tolist(),
                "lower_80": lower_80.tolist(),
                "upper_80": upper_80.tolist()
            }
            
        except Exception as e:
            logger.error(f"预测过程出错: {e}")
            raise e
