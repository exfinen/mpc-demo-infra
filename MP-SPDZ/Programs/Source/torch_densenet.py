# this tests the pretrained DenseNet in secure computation

program.options_from_args()
sfix.set_precision_from_args(program, adapt_ring=True)
MultiArray.disable_index_checks()
Array.check_indices = False

from Compiler import ml

try:
    ml.set_n_threads(int(program.args[2]))
except:
    pass

import torchvision
import torch
import numpy
import requests
import io
import PIL

from torchvision import transforms

model = getattr(torchvision.models.densenet, 'densenet' + program.args[1])(
    weights='DEFAULT')

r = requests.get('https://github.com/pytorch/hub/raw/master/images/dog.jpg')
input_image = PIL.Image.open(io.BytesIO(r.content))
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
input_tensor = preprocess(input_image)
input_batch = input_tensor.unsqueeze(0) # create a mini-batch as expected by the model

with torch.no_grad():
    output = int(model(input_batch).argmax())
    print('Model says %d' % output)

secret_input = sfix.input_tensor_via(
    0, numpy.moveaxis(input_batch.numpy(), 1, -1))

layers = ml.layers_from_torch(
    model, secret_input.shape, 1, input_via=0,
    layer_args={model.features.conv0: {'weight_type': sfix.get_prec_type(32)}})

optimizer = ml.Optimizer(layers)
optimizer.output_stats = 'output_stats' in program.args

print_ln('Secure computation says %s',
         optimizer.eval(secret_input, top=True)[0].reveal())
