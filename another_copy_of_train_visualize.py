# -*- coding: utf-8 -*-
"""Another copy of Train_Visualize.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1KD21vtpJdiOuASeOWxtTfpDASh4qCkK2
"""

from google.colab import drive
drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.
!git clone --single-branch --branch resnet50 https://github.com/cy6erlizard/object-detect.git
# %cd object-detect

pip install pycocotools

import matplotlib.pyplot as plt
import random

import torch

from torchvision import transforms
from dataset import prepare_dataset

# use same transform for train/val for this example
size = (450,675)
trans = transforms.Compose([
    transforms.ToTensor(),
    transforms.Resize(size),
    transforms.Normalize([0.3394, 0.3598, 0.3226], [0.2037, 0.1899, 0.1922]),
])

target_trans = transforms.Compose([
    transforms.ToTensor(),
    transforms.Resize(size),
])

dataset_dir = './NWPU VHR-10_dataset_coco'
train_annotations = f'{dataset_dir}/instances_train2017.json'
val_annotations = f'{dataset_dir}/instances_val2017.json'
images_path = f'{dataset_dir}/positive image set'

batch_size = 4
dataloaders, image_sets = prepare_dataset(images_path, train_annotations, val_annotations,
                              batch_size = batch_size, transform = trans, target_transform = target_trans)

train_set, val_set = image_sets['train'], image_sets['val']

print(f"Train_Image Count: {len(train_set.image_ids)},\
        Val Image Count: {len(val_set.image_ids)}")

print(f"Train Class Count: {train_set.num_classes}, Val Class Count: {val_set.num_classes}" )

for i, info in enumerate(train_set.class_info):
    print("{:3}. {:50}".format(i, info['name']))

import numpy as np
import torch.nn.functional as F
import torch

def denormalize(img,mean= [0.3394, 0.3598, 0.3226] , std = [0.2037, 0.1899, 0.1922]):
    img = img * np.array(std) + np.array(mean)
    return img

def to_rgb(mask, colors):
    C,H,W = mask.shape
    bg_channel = torch.zeros((1,H,W))
    mask = mask.cpu()
    mask  = torch.cat((bg_channel, mask), dim=0)
    mask = F.softmax(mask, dim=0).argmax(dim=0)
    mask = mask.cpu().detach().numpy()

    image = np.zeros((H,W,3))
    image = colors[mask]

    return image

np.random.seed(42)
colors = np.random.uniform(0,255, size=(train_set.num_classes+1,3))
count=0

from lib import visualize
from lib import utils

imgs, masks , ids = next(iter(dataloaders['train']))
x = 1
image, mask, id = imgs[x], masks[x], ids[x]

img = denormalize(image.permute(1,2,0).cpu().detach().numpy())*255.0

visualize.display_images([img, to_rgb(mask, colors) ], cols=2)
visualize.display_sematics(img, mask, colors, count)
count += 1

#Visualize Instance Masks
mask_1, class_ids = train_set.load_mask(id)
#mask_1 = mask_1.astype(np.uint8)

mask_1 = mask_1.astype(np.float32)
mask_1 = utils.resize(mask_1, size)
bbox = utils.extract_bboxes(mask_1)

visualize.display_instances(img, bbox, mask_1, class_ids, train_set.class_names)

!pip install torchsummary

from torchsummary import summary
from models.maskresnet50 import MaskResnet50

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(device)

model = MaskResnet50(n_blocks=[3, 4, 23, 3],n_classes=10, atrous_rates=[1,2,4,12]).to(device)
summary(model, (3,600,900))

from torch.optim import lr_scheduler
from train import train_model
import torch.optim as optim
import os

path = '/content/drive/MyDrive/Deeplab_models1/'

# if os.path.exists(path+ 'v2_r24812_2.pt'):
#     model.load_state_dict(torch.load(path+ 'v2_r24812_2.pt', map_location=device))
#     print('model weights loaded')

# # Observe that all parameters are being optimized
optimizer_ft = optim.Adam(model.parameters(), lr=5e-5)

num_epochs=2

lambda_lr = lr_scheduler.LambdaLR(optimizer_ft, lr_lambda=lambda epoch : (1-epoch/num_epochs)**(0.9))

model, losses, class_miou, total_miou = train_model(model, dataloaders, optimizer_ft, lambda_lr, num_epochs=num_epochs)
# torch.save(model.state_dict(), path+"v1_12412.pt")

# Save model checkpoint after the first epoch
checkpoint = {
    'epoch': 1,
    'state_dict': model.state_dict(),
    'optimizer': optimizer.state_dict(),
    # Add more information if needed
}
torch.save(checkpoint, 'model_checkpoint_epoch1.pth')

torch.save(model.state_dict(), path+"v1_12412.pt")

"""### Plot the loss and mIOU curves"""

plt.figure(figsize=(15,8))
plt.subplot(2,2,1)
epochs = len(losses['train'])
plt.plot(range(epochs), losses['train'], label="Train Loss")
plt.plot( range(epochs), losses['val'], label="Val Loss")
plt.legend()
plt.title("Loss")

plt.subplot(2,2,2)
plt.plot(range(epochs), total_miou['train'], label="Train mIOU")
plt.plot(range(epochs), total_miou['val'], label="Val mIOU")
plt.legend()
plt.title("mIOU")

plt.savefig("Loss_mIOU")

plt.figure(figsize=(15,15))
plt.subplot(2,1,1)
for cls in class_miou['train'].keys():
    plt.plot( range(epochs), class_miou['train'][cls], label=f'{train_set.class_info[cls-1]["name"]}')
plt.legend(loc=2)
plt.title("Training")

plt.subplot(2,1,2)
for cls in class_miou['val'].keys():
    plt.plot( range(epochs), class_miou['val'][cls], label=f'{train_set.class_info[cls-1]["name"]}')
plt.legend(loc=2)
plt.title("Validation")
plt.savefig("class_iou")

"""### Visualize the predictions"""

imgs, masks,_ = next(iter(dataloaders['val']))
for x in range(batch_size):
    image, mask  = imgs[x], masks[x]
    # print(mask.shape)
    C,H,W = image.shape
    rgb_mask = to_rgb(mask,colors)
    img_ = image.permute(1,2,0).cpu().detach().numpy()
    img_ = denormalize(img_)

    with torch.no_grad():
        pred = model(image.unsqueeze(0).to(device)).squeeze(0)

    # print(pred.shape)
    rgb_pred = to_rgb(pred, colors)

    visualize.display_images([img_*255, rgb_pred, rgb_mask],
                             titles=["image", 'prediction','ground truth'],cols=3)

def calc_avg_hw(dataset):
    heights = [dataset.image_info[i]['height'] for i in range(len(dataset.image_ids)) ]
    widths = [dataset.image_info[i]['width'] for i in range(len(dataset.image_ids))]
    return  [sum(heights)/len(heights),  sum(widths)/len(widths)]

# print(calc_avg_hw(train_set))

def calc(train_set):
    imgs = torch.stack([img for img,_,_ in train_set], dim = -1)
    print(imgs.shape)
    imgs = imgs.view(imgs.shape[0],-1)
    print(imgs.shape)
    mean = imgs.mean(dim = -1)
    std = imgs.std(dim=-1)
    print(mean, std)

calc(train_set)
