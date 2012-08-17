import re
import datetime

from django import forms


class MonthYearWidget(forms.MultiWidget):
    """
    Display two text inputs, for collecting a month and a year attribute.
    Useful for credit card expiry inputs
    """
    def __init__(self, *args, **kwargs):
        widgets = (
            forms.TextInput(
                attrs={'size': 2, 'maxlength': '2', 'class': 'input-small'}),
            forms.TextInput(
                attrs={'size': 4, 'maxlength': '4', 'class': 'input-small'}),
        )
        super(MonthYearWidget, self).__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return tuple(value)

        if isinstance(value, datetime.datetime):
            value = value.date()

        if isinstance(value, datetime.date):
            return (value.month, value.year)

        return (None, None)

    def value_from_datadict(self, data, files, name):
        bits = super(MonthYearWidget, self).value_from_datadict(data, files,
            name)

        value = None

        try:
            value = [int(str(bit)) for bit in bits]
        except ValueError:
            pass

        return value

    def format_output(self, rendered_widgets):
        return '%s / %s' % (rendered_widgets[0], rendered_widgets[1])


class MonthYearField(forms.MultiValueField):
    """
    Get a `(year, month)` tuple, such as a credit card expiry
    """
    widget = MonthYearWidget

    def __init__(self, add_century=False, strip_century=False, fields=None,
        *args, **kwargs):

        fields = fields if fields is not None else (
            forms.IntegerField(max_value=12, min_value=1),
            forms.IntegerField(min_value=0),
        )
        self.add_century = add_century
        self.strip_century = strip_century

        if self.add_century and self.strip_century:
            raise ValueError("add_century and strip_century can not both be"
                "True")

        super(MonthYearField, self).__init__(fields=fields, *args, **kwargs)

    def compress(self, values):
        values = list(values)

        month = 0
        year = 1

        if self.add_century and values[year] < 100:
            this_year = datetime.date.today().year
            this_century = (this_year / 100) * 100

            # The year is before the current year, so add a century.
            if (this_year % 100) > values[year]:
                values[year] += 100

            values[year] += this_century

        if self.strip_century and values[year] > 100:
            values[year] = values[year] % 100

        return tuple(values)


class CreditCardForm(forms.Form):
    """
    Collect credit card information from a user. This form includes all the
    data required to use the NAB Transact gateway.
    """
    name = forms.CharField(required=True, label="Name on card")

    CARD_TYPES = [
        ('MC', 'MasterCard'),
        ('VI', 'Visa'),
    ]
    card_type = forms.CharField(required=True, label="Card type",
        widget=forms.Select(choices=CARD_TYPES))

    number = forms.CharField(required=True)

    expiry = MonthYearField(required=True, strip_century=True,
        help_text='MM / YY')

    cvv = forms.IntegerField(min_value=0, max_value=9999,
        help_text="This is a three or four digit number, found on the back of"
            "your card")

    def clean_number(self):
        number = self.cleaned_data.get('number', None)
        if number:
            number = re.sub(r'[\D]', '', number)

        return number
