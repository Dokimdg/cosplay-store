from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomUser(AbstractUser):
    """Кастомна модель користувача для майбутнього розширення"""
    email = models.EmailField('Email', unique=True)

    class Meta:
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'


class UserProfile(models.Model):
    """Профіль користувача з інформацією для доставки"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Номер телефону')
    address = models.TextField(blank=True, verbose_name='Адреса доставки')
    nickname = models.CharField(max_length=100, blank=True, verbose_name='Косплей нікнейм')

    class Meta:
        verbose_name = 'Профіль користувача'
        verbose_name_plural = 'Профілі користувачів'

    def __str__(self):
        return f'Профіль: {self.user.username}'


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    # get_or_create: безпечно і для старих користувачів без профілю
    UserProfile.objects.get_or_create(user=instance)
