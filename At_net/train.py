# -*- coding: utf-8 -*-
# git clone https://github.com/zhanglideng/At_J_net.git
import sys
import torch
sys.path.append("..")
from torchvision import transforms
from torch.utils.data import DataLoader
from loss import *
from dataloader import *
from At_model import *
import time
import argparse
from utils import *
'''
LR = 0.0004  # 学习率
EPOCH = 40  # 轮次
BATCH_SIZE = 1  # 批大小
excel_train_line = 1  # train_excel写入的行的下标
excel_val_line = 1  # val_excel写入的行的下标
alpha = 1  # 损失函数的权重
accumulation_steps = 8  # 梯度积累的次数，类似于batch-size=64
# itr_to_lr = 10000 // BATCH_SIZE  # 训练10000次后损失下降50%
itr_to_excel = 8 // BATCH_SIZE  # 训练64次后保存相关数据到excel

weight = [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1]
loss_num = len(weight)  # 包括参加训练和不参加训练的loss
'''

# --- Parse hyper-parameters  --- #
parser = argparse.ArgumentParser(description='Hyper-parameters for At_Net')
parser.add_argument('-learning_rate', help='Set the learning rate', default=5e-4, type=float)
parser.add_argument('-batch_size', help='Set the training batch size', default=1, type=int)
parser.add_argument('-accumulation_steps', help='Set the accumulation steps', default=16, type=int)
parser.add_argument('-drop_rate', help='Set the dropout ratio', default=0, type=int)
parser.add_argument('-itr_to_excel', help='Save to excel after every n trainings', default=128, type=int)
parser.add_argument('-epoch', help='Set the epoch', default=100, type=int)
parser.add_argument('-category', help='Set image category (NYU or NTIRE?)', default='FIVEK/fivek4.11/', type=str)
parser.add_argument('-data_path', help='Set the data_path', default='/Volumes/Amber‘s HP/zld/', type=str)
parser.add_argument('-pre_model', help='Whether to use a pre-trained model', default=False, type=bool)
parser.add_argument('-inter_train', help='Is the training interrupted', default=False, type=bool)
parser.add_argument('-MAE_or_MSE', help='Use MSE or MAE', default='MAE', type=str)
parser.add_argument('-IN_or_BN', help='Use IN or BN', default='IN', type=str)
parser.add_argument('-loss_weight', help='Set the loss weight', default=[1, 1, 1, 1, 1, 1], type=list)

parser.add_argument('-excel_row', help='The excel row',
                    default=[["epoch", "itr", "A_l1", "t_l1", "J_l1", "loss"],
                             ["epoch", "A_l1", "t_l1", "t_ssim", "J_l1", "J_ssim", "J_vgg", "val_loss", "train_loss"]],
                    type=list)
args = parser.parse_args()

learning_rate = args.learning_rate  # 学习率
accumulation_steps = args.accumulation_steps  # 梯度累积
batch_size = args.batch_size  # 批大小
epoch = args.epoch  # 轮次
drop_rate = args.drop_rate  # dropout的比例
category = args.category  # NYU或NTIRE训练集
itr_to_excel = args.itr_to_excel  # 每训练itr次保存到excel中
weight = args.loss_weight  # 损失函数权重
loss_num = len(weight)  # 损失函数的数量
data_path = args.data_path  # 数据存放的路径
Is_pre_model = args.pre_model  # 是否使用预训练模型
Is_inter_train = args.inter_train  # 是否是被中断的训练
MAE_or_MSE = args.MAE_or_MSE  # 使用MSE还是MAE
excel_row = args.excel_row  # excel的列属性名
norm_type = args.IN_or_BN  # 使用实例归一化还是批归一化

# 加载模型
if Is_inter_train:
    print('加载中断后模型')
    net = torch.load('./mid_model/At_model.pt').cuda()
elif Is_pre_model:
    print('加载预训练模型')
    net = torch.load(data_path + '/pre_model/At_model/best_At_model.pt').cuda()
else:
    print('创建新模型')
    net = At_net(drop_rate=drop_rate, norm_type=norm_type).cuda()
    # print(net)
loss_net = train_loss_net(pixel_loss=MAE_or_MSE).cuda()

# 计算模型参数数量
total_params = sum(p.numel() for p in net.parameters() if p.requires_grad)
print("Total_params: {}".format(total_params))

# 读取数据集目录
if category == 'fiveK':
    train_hazy_path = data_path + '/data/FIVEK/fivek4.11/train_haze/'
    val_hazy_path = data_path + '/data/FIVEK/fivek4.11/val_haze/'
    train_gth_path = data_path + '/data/FIVEK/fivek4.11/gt/'
    val_gth_path = data_path + '/data/FIVEK/fivek4.11/gt/'
    train_t_path = data_path + '/data/FIVEK/fivek4.11/guide_t/'
    val_t_path = data_path + '/data/FIVEK/fivek4.11/guide_t/'

    train_A_path = data_path + '/data/nyu/train_A_patch/'
    val_A_path = data_path + '/data/nyu/val_A_patch/'
    train_path_list = [train_hazy_path, train_gth_path, train_t_path, train_A_path]
    val_path_list = [val_hazy_path, val_gth_path, val_t_path, val_A_path]
else:
    # train_hazy_path = data_path + '/data/ntire/train_hazy_patch/'
    # val_hazy_path = data_path + '/data/ntire/val_hazy_patch/'
    # train_gth_path = data_path + '/data/ntire/train_gth_patch/'
    # val_gth_path = data_path + '/data/ntire/val_gth_patch/'
    # train_path_list = [train_hazy_path, train_gth_path]
    # val_path_list = [val_hazy_path, val_gth_path]
    print("no fiveK")

# train_path_list, val_path_list, save_path, save_model_name, excel_save, mid_model = get_train_path(net_name, data_path,
#                                                                                                    category)

save_path = data_path + '/train_result/At_result_' + time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime()) + '/'
save_model_name = save_path + 'At_model.pt'  # 保存模型的路径
excel_save = save_path + 'result.xls'  # 保存excel的路径
mid_save_ed_path = './mid_model/At_model.pt'  # 保存的中间模型，用于意外停止后继续训练。
log = 'learning_rate: {}\nbatch_size: {}\nepoch: {}\ndrop_rate: {}\ncategory: {}\n' \
      'loss_weight: {}\nIs_pre_model: {}\ntotal_params: {}\nsave_file_name: {}\n' \
      'MAE_or_MSE: {}\nIs_inter_train: {}\naccumulation_steps: {}\nnorm_type: {}'.format(learning_rate, batch_size,
                                                                                         epoch, drop_rate, category,
                                                                                         weight, Is_pre_model,
                                                                                         total_params, save_path,
                                                                                         MAE_or_MSE, Is_inter_train,
                                                                                         accumulation_steps, norm_type)

print('--- Hyper-parameters for training ---')
print(log)

# 创建用于临时保存的文件夹
if not os.path.exists('./mid_model'):
    os.makedirs('./mid_model')

# 创建本次训练的保存文件夹并记录重要信息
if not os.path.exists(save_path):
    os.makedirs(save_path)
with open(save_path + 'detail.txt', 'w') as f:
    f.write(log)

# 创建用于保存训练和验证过程的表格文件
excel_train_line = 1
excel_val_line = 1
f, sheet_train, sheet_val = init_train_excel(row=excel_row)

# 创建图像数据加载器
transform = transforms.Compose([transforms.ToTensor()])

if category == 'fiveK':
    train_data = train_DataSet(transform, train_path_list)
    val_data = train_DataSet(transform, val_path_list)
else:
    # train_data = Ntire_DataSet(transform, train_path_list)
    # val_data = Ntire_DataSet(transform, val_path_list)
    print('no this dataset')
train_data_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, num_workers=8)
val_data_loader = DataLoader(val_data, batch_size=batch_size, shuffle=True, num_workers=8)

# 定义优化器
optimizer = torch.optim.Adam(net.parameters(), lr=learning_rate, weight_decay=1e-5)
# scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=40, gamma=0.5)


# 开始训练
min_loss = 99999
start_time = time.time()
print("\nstart to train!")
for epo in range(epoch):
    index = 0
    train_loss = 0
    loss_excel = [0] * loss_num
    net.train()
    for name, haze_image, gt_image, A_gth, t_gth in train_data_loader:
        index += 1
        haze_image = haze_image.cuda()
        gt_image = gt_image.cuda()
        A_gth = A_gth.cuda()
        t_gth = t_gth.cuda()
        A, t, J_reconstruct = net(haze_image)
        loss_image = [A, A_gth, t, t_gth, J_reconstruct, gt_image]
        loss, temp_loss = loss_net(loss_image, weight)

        train_loss += loss.item()
        loss_excel = [loss_excel[i] + temp_loss[i] for i in range(len(loss_excel))]
        loss = loss / accumulation_steps
        loss.backward()

        if ((index + 1) % accumulation_steps) == 0:
            optimizer.step()  # update parameters of net
            optimizer.zero_grad()  # reset gradient
        if np.mod(index, itr_to_excel) == 0:
            loss_excel = [loss_excel[i] / itr_to_excel for i in range(len(loss_excel))]
            print('epoch %d, %03d/%d' % (epo + 1, index, len(train_data_loader)))
            print('train loss = {}\n'.format(loss_excel))
            print_time(start_time, index, epoch, len(train_data_loader), epo)

    optimizer.step()
    optimizer.zero_grad()
    loss_excel = [0] * loss_num
    val_loss = 0
    with torch.no_grad():
        net.eval()
        for name, haze_image, gt_image, A_gth, t_gth in val_data_loader:
            haze_image = haze_image.cuda()
            gt_image = gt_image.cuda()
            A_gth = A_gth.cuda()
            t_gth = t_gth.cuda()
            A, t, J_reconstruct = net(haze_image)
            loss_image = [A, A_gth, t, t_gth, J_reconstruct, gt_image]
            loss, temp_loss = loss_net(loss_image, weight)
            loss_excel = [loss_excel[i] + temp_loss[i] for i in range(len(loss_excel))]
    train_loss = train_loss / len(train_data_loader)
    loss_excel = [loss_excel[i] / len(val_data_loader) for i in range(len(loss_excel))]
    for i in range(len(loss_excel)):
        val_loss = val_loss + loss_excel[i] * weight[i]
    print('val loss = {}\n'.format(loss_excel))
    excel_val_line = write_excel_val(sheet=sheet_val, line=excel_val_line, epoch=epo,
                                     loss=[loss_excel, val_loss, train_loss])
    f.save(excel_save)
    if val_loss < min_loss:
        min_loss = val_loss
        min_epoch = epo
        torch.save(net, save_model_name)
        torch.save(net, mid_save_ed_path)
        print('saving the epoch %d model with %.5f' % (epo + 1, min_loss))
print('Train is Done!')
