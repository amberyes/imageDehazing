# -*- coding: utf-8 -*-
# git clone https://github.com/zhanglideng/J_net.git
import sys

sys.path.append("..")
from utils import *
from dataloader_fiveK import TrainDataSet
import torch
from torchvision import transforms
from torch.utils.data import DataLoader
from loss_fivek import *
from J_model import *
import time
import argparse

# --- Parse hyper-parameters  --- #
parser = argparse.ArgumentParser(description='Hyper-parameters for J_Net')
parser.add_argument('-net_name', help='Set the net_name', default='J', type=str)  # 5e-4
parser.add_argument('-learning_rate', help='Set the learning rate', default=1e-3, type=float)  # 5e-4
parser.add_argument('-batch_size', help='Set the training batch size', default=6, type=int)
parser.add_argument('-accumulation_steps', help='Set the accumulation steps', default=1, type=int)
parser.add_argument('-drop_rate', help='Set the dropout ratio', default=0, type=int)
parser.add_argument('-itr_to_excel', help='Save to excel after every n trainings', default=16, type=int)
parser.add_argument('-epoch', help='Set the epoch', default=300, type=int)
parser.add_argument('-category', help='Set image category', default='FIVEK/fiveK2.1/', type=str)
parser.add_argument('-data_path', help='Set the data_path', default='/home/liu/zhanglideng/', type=str)
parser.add_argument('-pre_model', help='Whether to use a pre-trained model', default=False, type=bool)
parser.add_argument('-inter_train', help='Is the training interrupted', default=False, type=bool)
parser.add_argument('-MAE_or_MSE', help='Use MSE or MAE', default='MAE', type=str)
parser.add_argument('-SSIM', help='Use MS-SSIM or SSIM', default='MS-SSIM', type=str)
parser.add_argument('-IN_or_BN', help='Use IN or BN', default='IN', type=str)
parser.add_argument('-loss_weight', help='Set the loss weight', default=[1, 1, 1], type=list)
parser.add_argument('-excel_row', help='The excel row',
                    default=[["epoch", "itr", "loss"],
                             ["epoch", "MAE", "val_loss", "train_loss"]],
                    type=list)

args = parser.parse_args()

net_name = args.net_name  # ????????????
learning_rate = args.learning_rate  # ?????????
accumulation_steps = args.accumulation_steps  # ????????????
batch_size = args.batch_size  # ?????????
epoch = args.epoch  # ??????
drop_rate = args.drop_rate  # dropout?????????
category = args.category  # ?????????????????????
itr_to_excel = args.itr_to_excel  # ?????????itr????????????excel???
weight = args.loss_weight  # ??????????????????
loss_num = len(weight)  # ?????????????????????
data_path = args.data_path  # ?????????????????????
Is_pre_model = args.pre_model  # ???????????????????????????
Is_inter_train = args.inter_train  # ???????????????????????????
MAE_or_MSE = args.MAE_or_MSE  # ??????MSE??????MAE
SSIM = args.SSIM  # ??????MS-SSIM??????SSIM
excel_row = args.excel_row  # excel???????????????
norm_type = args.IN_or_BN  # ???????????????????????????????????????

# ????????????
if Is_inter_train:
    print('?????????????????????')
    net = torch.load('./mid_model/J_model.pt')
elif Is_pre_model:
    print('?????????????????????')
    net = torch.load(data_path + '/pre_model/J_model/best_J_model.pt')
else:
    print('???????????????')
    net = J_net(drop_rate=drop_rate, norm_type=norm_type)

loss_net = fiveK_loss(pixel_loss=MAE_or_MSE).cuda()

# ????????????????????????
count_params(net)

# ???????????????????????????
transform = transforms.Compose([transforms.ToTensor()])

# ?????????????????????
train_path_list, val_path_list, save_path, save_model_name, excel_save, mid_model = get_train_path(net_name, data_path,
                                                                                                   category)

log = 'learning_rate: {}\nbatch_size: {}\nepoch: {}\ndrop_rate: {}\ncategory: {}\n' \
      'loss_weight: {}\nIs_pre_model: {}\nsave_file_name: {}\n' \
      'MAE_or_MSE: {}\nIs_inter_train: {}\naccumulation_steps: {}\nnorm_type: {}'.format(learning_rate, batch_size,
                                                                                         epoch, drop_rate, category,
                                                                                         weight, Is_pre_model,
                                                                                         save_path,
                                                                                         MAE_or_MSE, Is_inter_train,
                                                                                         accumulation_steps, norm_type)

print('--- Hyper-parameters for training ---')
print(log)

# ????????????????????????????????????
create_dir('./mid_model')
# ?????????????????????????????????????????????????????????
create_dir(save_path)
with open(save_path + 'detail.txt', 'w') as f:
    f.write(log)
# ??????????????????????????????????????????????????????
excel_train_line = 1
excel_val_line = 1
f, sheet_train, sheet_val = init_train_excel(row=excel_row)

train_data = TrainDataSet(transform, train_path_list, data_aug=True)
val_data = TrainDataSet(transform, val_path_list)

train_data_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, num_workers=8)
val_data_loader = DataLoader(val_data, batch_size=batch_size, shuffle=False, num_workers=8)

# ???????????????
optimizer = torch.optim.Adam(net.parameters(), lr=learning_rate, weight_decay=1e-5)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.5)

# ????????????
min_loss = 99999
start_time = time.time()
print("\nstart to train!")
for epo in range(epoch):
    index = 0
    train_loss = 0
    loss_excel = [0] * loss_num
    net.train()
    net.cuda()
    for name, haze_image, gt_image in train_data_loader:
        index += 1

        haze_image = haze_image.cuda()
        gt_image = gt_image.cuda()

        J = net(haze_image)

        loss_image = [J, gt_image]
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
            print('train loss = {}'.format(loss_excel))
            print_time(start_time, index, epoch, len(train_data_loader), epo)
    scheduler.step()
    optimizer.step()
    optimizer.zero_grad()
    loss_excel = [0] * loss_num
    val_loss = 0
    with torch.no_grad():
        net.eval()
        for name, haze_image, gt_image in val_data_loader:
            haze_image = haze_image.cuda()
            gt_image = gt_image.cuda()

            J = net(haze_image)

            loss_image = [J, gt_image]
            loss, temp_loss = loss_net(loss_image, weight)
            loss_excel = [loss_excel[i] + temp_loss[i] for i in range(len(loss_excel))]
    train_loss = train_loss / len(train_data_loader)
    loss_excel = [loss_excel[i] / len(val_data_loader) for i in range(len(loss_excel))]
    for i in range(len(loss_excel)):
        val_loss = val_loss + loss_excel[i] * weight[i]
    print('val loss = {}'.format(loss_excel))
    excel_val_line = write_excel_val(sheet=sheet_val, line=excel_val_line, epoch=epo,
                                     loss=[loss_excel, val_loss, train_loss])
    f.save(excel_save)
    if val_loss < min_loss:
        min_loss = val_loss
        min_epoch = epo
        torch.save(net.cpu(), save_model_name)
        torch.save(net.cpu(), mid_model)
        print('saving the epoch %d model with %.5f\n' % (epo + 1, min_loss))
print('Train is Done!')
