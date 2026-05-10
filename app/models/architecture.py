"""
Model architectures for the steganography pipeline.
These MUST match the training architecture exactly — do not modify.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CSPBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        sp = max(in_channels // 2, 1)
        self.sp = sp
        self.part1 = nn.Sequential(
            nn.Conv2d(sp, sp, 3, padding=1, bias=False),
            nn.BatchNorm2d(sp),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(sp, sp, 3, padding=1, bias=False),
            nn.BatchNorm2d(sp),
            nn.LeakyReLU(0.2, inplace=True),
        )
        self.transition = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.LeakyReLU(0.2, inplace=True),
        )

    def forward(self, x):
        return self.transition(
            torch.cat((self.part1(x[:, : self.sp]), x[:, self.sp :]), dim=1)
        )


class SEBlock(nn.Module):
    def __init__(self, channels, reduction=8):
        super().__init__()
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(channels, max(channels // reduction, 4)),
            nn.ReLU(inplace=True),
            nn.Linear(max(channels // reduction, 4), channels),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return x * self.se(x).view(x.size(0), x.size(1), 1, 1)


class Generator(nn.Module):
    """Encoder/Hider — takes (cover, secret) and produces a residual."""

    def __init__(self):
        super().__init__()
        self.initial = nn.Sequential(
            nn.Conv2d(6, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.2, inplace=True),
        )
        self.csp1 = CSPBlock(64, 128)
        self.down1 = nn.Sequential(
            nn.Conv2d(128, 128, 4, 2, 1, bias=False),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.2, inplace=True),
        )
        self.csp2 = CSPBlock(128, 128)
        self.se = SEBlock(128, reduction=8)
        self.csp3 = CSPBlock(128, 64)
        self.refine = nn.Sequential(
            nn.Conv2d(64, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.2, inplace=True),
        )
        self.final = nn.Sequential(nn.Conv2d(64, 3, 1), nn.Tanh())

    def forward(self, cover, secret):
        x = self.initial(torch.cat((cover, secret), dim=1))
        x = self.csp1(x)
        x = self.down1(x)
        x = self.csp2(x)
        x = self.se(x)
        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        return self.final(self.refine(self.csp3(x)))


class ResConvBlock(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_ch)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_ch)
        self.relu = nn.ReLU(inplace=True)
        self.skip = nn.Conv2d(in_ch, out_ch, 1, bias=False) if in_ch != out_ch else None

    def forward(self, x):
        identity = self.skip(x) if self.skip else x
        return self.relu(
            self.bn2(self.conv2(self.relu(self.bn1(self.conv1(x))))) + identity
        )


class DeepUNetDecoder(nn.Module):
    """Reveal network — recovers the secret from the stego image."""

    def __init__(self, in_channels=3, base=32):
        super().__init__()
        self.enc1 = ResConvBlock(in_channels, base)
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = ResConvBlock(base, base * 2)
        self.pool2 = nn.MaxPool2d(2)
        self.enc3 = ResConvBlock(base * 2, base * 4)
        self.pool3 = nn.MaxPool2d(2)
        self.enc4 = ResConvBlock(base * 4, base * 8)
        self.pool4 = nn.MaxPool2d(2)
        self.enc5 = ResConvBlock(base * 8, base * 8)
        self.pool5 = nn.MaxPool2d(2)
        self.bottleneck = nn.Sequential(
            ResConvBlock(base * 8, base * 16),
            nn.Dropout2d(0.15),
            ResConvBlock(base * 16, base * 16),
        )
        self.up1 = nn.ConvTranspose2d(base * 16, base * 8, 2, 2)
        self.dec1 = ResConvBlock(base * 16, base * 8)
        self.up2 = nn.ConvTranspose2d(base * 8, base * 8, 2, 2)
        self.dec2 = ResConvBlock(base * 16, base * 8)
        self.up3 = nn.ConvTranspose2d(base * 8, base * 4, 2, 2)
        self.dec3 = ResConvBlock(base * 8, base * 4)
        self.up4 = nn.ConvTranspose2d(base * 4, base * 2, 2, 2)
        self.dec4 = ResConvBlock(base * 4, base * 2)
        self.up5 = nn.ConvTranspose2d(base * 2, base, 2, 2)
        self.dec5 = ResConvBlock(base * 2, base)
        self.final_conv = nn.Conv2d(base, 3, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        e3 = self.enc3(self.pool2(e2))
        e4 = self.enc4(self.pool3(e3))
        e5 = self.enc5(self.pool4(e4))
        b = self.bottleneck(self.pool5(e5))
        d1 = self.dec1(torch.cat([self.up1(b), e5], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d1), e4], dim=1))
        d3 = self.dec3(torch.cat([self.up3(d2), e3], dim=1))
        d4 = self.dec4(torch.cat([self.up4(d3), e2], dim=1))
        d5 = self.dec5(torch.cat([self.up5(d4), e1], dim=1))
        return torch.tanh(self.final_conv(d5))
