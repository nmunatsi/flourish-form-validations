from django.apps import apps as django_apps
from django.forms import ValidationError
from edc_form_validators import FormValidator

from .crf_form_validator import FormValidatorMixin


class SocioDemographicDataFormValidator(FormValidatorMixin, FormValidator):

    antenatal_enrollment_model = 'flourish_caregiver.antenatalenrollment'
    preg_women_screening_model = 'flourish_caregiver.screeningpregwomen'
    delivery_model = 'flourish_caregiver.maternaldelivery'
    maternal_dataset_model = 'flourish_caregiver.maternaldataset'
    child_socio_demographic_model = 'flourish_child.childsociodemographic'

    @property
    def maternal_dataset_cls(self):
        return django_apps.get_model(self.maternal_dataset_model)

    @property
    def antenatal_enrollment_cls(self):
        return django_apps.get_model(self.antenatal_enrollment_model)

    @property
    def preg_screening_cls(self):
        return django_apps.get_model(self.preg_women_screening_model)

    @property
    def delivery_model_cls(self):
        return django_apps.get_model(self.delivery_model)
    
    @property
    def child_socio_demographic_cls(self):
        return django_apps.get_model(self.child_socio_demographic_model)

    def clean(self):
        self.subject_identifier = self.cleaned_data.get(
            'maternal_visit').subject_identifier
        super().clean()
        

        other_specify_fields = ['marital_status', 'ethnicity',
                                'current_occupation', 'provides_money',
                                'money_earned', 'toilet_facility']
        for field in other_specify_fields:
            self.validate_other_specify(field=field)

        if not self.is_from_prev_study:
            self.applicable_if_true(self.is_not_pregnant, 'stay_with_child')
            self.required_if_true(not self.is_not_pregnant, 'number_of_household_members')
            
        self.validate_child_socio_demographics()

    @property
    def is_from_prev_study(self):

        maternal_visit = self.cleaned_data.get('maternal_visit')

        return self.maternal_dataset_cls.objects.filter(
            subject_identifier=maternal_visit.subject_identifier).exists()

    @property
    def is_not_pregnant(self):

        maternal_visit = self.cleaned_data.get('maternal_visit')
        try:
            self.preg_screening_cls.objects.get(
                subject_identifier=maternal_visit.subject_identifier)
        except self.preg_screening_cls.DoesNotExist:
            return True
        else:
            try:
                self.delivery_model_cls.objects.get(
                    subject_identifier=maternal_visit.subject_identifier)
            except self.delivery_model_cls.DoesNotExist:
                return False
            else:
                return True
            
    @property
    def onschedule_cls(self):
        maternal_visit = self.cleaned_data.get('maternal_visit')
        return django_apps.get_model(
            maternal_visit.appointment.schedule.onschedule_model
        )
    
    def validate_child_socio_demographics(self):
        
        visit_code = self.cleaned_data.get('maternal_visit').visit_code[:4]
        
        try:
        
            on_schedule_obj = self.onschedule_cls.objects.get(
                subject_identifier=self.subject_identifier)
        except self.onschedule_cls.DoesNotExist:
            pass
        else:
            child_subject_identifier = on_schedule_obj.child_subject_identifier
            
            try:
                child_sociodemographics = self.child_socio_demographic_cls.objects.get(
                    child_visit__visit_code__istartswith = visit_code,
                    child_visit__subject_identifier = child_subject_identifier,
                )
            except self.child_socio_demographic_cls.DoesNotExist:
                pass
            else:
                
                stay_with_child = self.cleaned_data.get('stay_with_child')
                
                if child_sociodemographics.stay_with_caregiver != stay_with_child:
                    raise ValidationError({'stay_with_child': 'The response don\'t match with the '
                                           f' Child Social demographics CRF at visit {child_sociodemographics.visit_code}'})
        
        
