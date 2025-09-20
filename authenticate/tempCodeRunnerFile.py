# class CustomUser(AbstractBaseUser, PermissionsMixin):
#     first_name   = models.CharField(max_length=50)
#     last_name    = models.CharField(max_length=50)
#     email        = models.EmailField(unique=True)
#     phone_number = models.CharField(max_length=15, unique=True)
#     # … rest unchanged …