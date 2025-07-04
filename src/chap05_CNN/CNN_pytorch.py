#!/usr/bin/env python
# coding: utf-8

# 导入必要的库
# 导入操作系统模块，用于环境变量设置、路径管理等系统相关操作
import os

# 导入 NumPy，用于高效的数值计算（如矩阵、向量操作）
import numpy as np

# 导入 PyTorch 主库
import torch

# 从 PyTorch 中导入神经网络模块（构建模型的基础类和层）
import torch.nn as nn

# 导入常用的函数接口模块，包括激活函数、损失函数等
import torch.nn.functional as F

# 从 PyTorch 中导入自动求导模块，用于构建支持梯度的变量
from torch.autograd import Variable

# 导入数据处理模块，包括 Dataset 封装与 DataLoader 批处理等功能
import torch.utils.data as Data

# 导入 torchvision 库，它包含了常用的计算机视觉数据集、模型结构和图像处理工具
import torchvision

# 设置超参数。超参数（Hyperparameters）是机器学习模型在训练前需要手动设定（或通过算法优化）的配置参数，
# 它们不直接从数据中学习，而是控制模型的整体行为和性能。
learning_rate = 1e-4  #  学习率：控制参数更新步长
keep_prob_rate = 0.7  #  Dropout保留神经元的比例：防止过拟合
max_epoch = 3         # 训练的总轮数
BATCH_SIZE = 50       # 每批训练数据的大小为50：影响内存使用和训练稳定性

# 检查是否需要下载 MNIST 数据集
DOWNLOAD_MNIST = False
if not(os.path.exists('./mnist/')) or not os.listdir('./mnist/'):
    # 如果不存在 mnist 目录或者目录为空，则需要下载
    DOWNLOAD_MNIST = True

# 加载训练数据集
train_data = torchvision.datasets.MNIST(
    root='./mnist/',                              # 数据集保存路径
    train=True,                                   # 加载训练集（False则加载测试集）
    transform=torchvision.transforms.ToTensor(),  # 将PIL图像转换为 Tensor 并归一化到[0,1]
    download=DOWNLOAD_MNIST                       # 如果需要则下载
)

# 创建数据加载器，用于批量加载数据
train_loader = Data.DataLoader(
    dataset=train_data,     # 使用的数据集
    batch_size=BATCH_SIZE,  # 每批数据量
    shuffle=True            # 是否在每个epoch打乱数据顺序（重要！避免模型学习到顺序信息）
)

# 加载测试数据集（不用于训练，仅用于评估）
# torchvision.datasets.MNIST用于加载 MNIST 数据集
# root='./mnist/'指定数据集的存储路径
# train=False表示加载测试集（而不是训练集）
test_data = torchvision.datasets.MNIST(root='./mnist/', train=False)
# 预处理测试数据：转换为 Variable（旧版PyTorch自动求导机制） ，调整维度（原始MNIST是28x28，需要变为1x28x28），转换为FloatTensor类型，归一化到[0,1]范围（/255.），只取前500个样本
test_x = Variable(torch.unsqueeze(test_data.test_data, dim=1), volatile=True).type(torch.FloatTensor)[:500]/255.
# 获取测试集的标签（前500个），并转换为 numpy 数组
test_y = test_data.test_labels[:500].numpy()

# 定义CNN模型
class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()                                # 调用父类构造函数
        """
        设计特点:
        使用小尺寸卷积核(3x3)保留更多局部特征
        - 批量归一化(BN)加速训练收敛
        - 最大池化逐步降低空间维度
        - Dropout层防止过拟合
        """
        # 第一个卷积层
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1),  # 3x3卷积核
            nn.BatchNorm2d(32),                                    # 添加批量归一化
            nn.ReLU(),                                             # ReLU激活函数，引入非线性，ReLU 函数的公式为 f(x) = max(0, x)，可以将负值置为0。
            nn.MaxPool2d(2)                                        # 最大池化，减小特征图尺寸
        )
        
        # 第二个卷积层
        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),  # 3x3卷积核
            nn.BatchNorm2d(64),                                     # 添加批量归一化
            nn.ReLU(),                                              # ReLU激活函数
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1),  # 增加一层3x3卷积
            nn.BatchNorm2d(64),                                     # 批量归一化，加速训练并提高模型稳定性
            nn.ReLU(),                                              # ReLU激活函数，引入非线性变换
            nn.MaxPool2d(2)                                         # 最大池化，减小特征图尺寸
        )
        
        # 第一个全连接层：输入是7*7*64=3136（两次池化后图像尺寸变为7x7），输出1024维
        self.out1 = nn.Linear(7*7*64, 1024, bias=True)
        
        # Dropout层：训练时随机丢弃神经元，防止过拟合
        self.dropout = nn.Dropout(keep_prob_rate)
        
        # 第二个全连接层：1024维输入，10维输出（对应10个数字类别）
        self.out2 = nn.Linear(1024, 10, bias=True)

    #定义了一个神经网络的前向传播过程，进行特征提取和分类预测
    def forward(self, x):
        x = self.conv1(x)          # 第一卷积层特征提取，输入 -> 卷积 -> 激活 (ReLU由self.conv1定义)
        x = self.conv2(x)          # 第二卷积层特征提取，特征图 -> 卷积 -> 激活
        x = x.view(x.size(0), -1)  # 展平张量：保留批量维度，合并其他所有维度
        out1 = self.out1(x)        # 第一个全连接层 + 激活函数，线性变换: [B, in_features] -> [B, hidden_features]
        out1 = F.relu(out1)        # 应用ReLU激活函数引入非线性
        out1 = self.dropout(out1)  # 应用dropout正则化，随机丢弃部分神经元输出
        out2 = self.out2(out1)     # 将上一层输出out1传递给当前层self.out2进行处理
        return out2

# 测试函数 - 评估模型在测试集上的准确率
def test(cnn):
    global prediction  # 使用全局变量prediction保存预测结果
    
    # 模型预测：输入测试数据，得到原始输出logits（未归一化的预测值）
    y_pre = cnn(test_x)  
    
    # 计算softmax概率分布（将logits转换为概率值，dim=1表示对类别维度做归一化）
    y_prob = F.softmax(y_pre, dim=1)
    
    # 获取预测类别：找到每个样本概率最大的类别索引
    # torch.max返回(最大值, 最大值的索引)
    _, pre_index = torch.max(y_prob, 1) 
    
    # 调整张量形状为1维向量（例如从[N,1]变为[N]）
    pre_index = pre_index.view(-1)
    
    # 将预测结果从PyTorch张量转换为numpy数组
    prediction = pre_index.data.numpy()
    
    # 计算正确预测的数量（预测值与真实标签test_y比较）
    correct = np.sum(prediction == test_y)
    
    # 返回准确率（假设测试集共500个样本）
    return correct / 500.0  


# 训练函数
def train(cnn):
    # 使用Adam优化器，学习率为learning_rate
    optimizer = torch.optim.Adam(cnn.parameters(), lr=learning_rate)
    # 使用交叉熵损失函数
    loss_func = nn.CrossEntropyLoss()

    # 训练max_epoch轮
    for epoch in range(max_epoch):
        # 遍历训练数据加载器
        for step, (x_, y_) in enumerate(train_loader):
            # 将数据转换为Variable（自动求导需要）
            x, y = Variable(x_), Variable(y_)
            output = cnn(x)                         # 前向传播得到预测结果
            loss = loss_func(output, y)             # 计算损失
            optimizer.zero_grad(set_to_none=True)   # 清空模型参数的梯度缓存，set_to_none=True可减少内存占用
            loss.backward()                         # 反向传播计算梯度
            optimizer.step()                        # 更新参数

            # 每20个batch打印一次测试准确率
            if step != 0 and step % 20 == 0:        # 跳过初始训练前的测试（通常初始准确率无意义）
                print("=" * 10, step, "=" * 5, "=" * 5, "测试准确率: ", test(cnn), "=" * 10)
                # step != 0: 跳过初始训练前的测试（通常初始准确率无意义）
# 主程序入口
if __name__ == '__main__':
    cnn = CNN()  # 创建CNN实例
    train(cnn)   # 开始训练
