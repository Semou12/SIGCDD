from django.core.exceptions import ValidationError

def only_digit_validator(value):
	if value.isdigit()==False:
		raise ValidationError('Uniquement des nombres')



from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


