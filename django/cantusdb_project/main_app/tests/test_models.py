from django.forms import ValidationError
from django.test import TestCase
from django.urls import reverse
from main_app.models import (
    Century,
    Chant,
    Feast,
    Genre,
    Office,
    Sequence,
    Source,
)
from .make_fakes import (
    make_fake_century,
    make_fake_chant,
    make_fake_feast,
    make_fake_genre,
    make_fake_office,
    make_fake_sequence,
    make_fake_source,
)

# run with `python -Wa manage.py test main_app.tests.test_models`
# the -Wa flag tells Python to display deprecation warnings


class CenturyModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up non-modified objects used by all test methods
        make_fake_century()

    def test_name_label(self):
        # Using first() is better than hardcoding the pk like Century.objects.get(pk=1)
        # because the pk sequence is not reset between test cases,
        # even though objects created by other tests are removed from db
        century = Century.objects.first()
        field_label = century._meta.get_field("name").verbose_name
        self.assertEqual(field_label, "name")

    def test_name_max_length(self):
        century = Century.objects.first()
        max_length = century._meta.get_field("name").max_length
        self.assertEqual(max_length, 255)

    def test_display_name(self):
        century = Century.objects.first()
        display_name = century.display_name
        name_str = century.__str__()
        self.assertEqual(display_name, name_str)


class ChantModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        source = make_fake_source()
        make_fake_chant(source=source)

    def test_get_ci_url(self):
        chant = Chant.objects.first()
        ci_url = chant.get_ci_url()
        ci_url_correct = "https://cantusindex.org/id/{}".format(chant.cantus_id)
        self.assertEqual(ci_url, ci_url_correct)

    def test_index_components(self):
        chant = Chant.objects.first()
        weight_search_term_dict = chant.index_components()
        expected_dict = {
            "A": (
                " ".join(
                    filter(
                        None,
                        [
                            chant.incipit,
                            chant.manuscript_full_text,
                            chant.manuscript_full_text_std_spelling,
                            chant.source.title,
                        ],
                    )
                )
            ),
            "B": (
                " ".join(
                    filter(
                        None, [chant.genre.name, chant.feast.name, chant.office.name]
                    )
                )
            ),
        }
        self.assertEqual(weight_search_term_dict, expected_dict)

    def test_get_concordances(self):
        chant = Chant.objects.get(id=1)
        chant_with_same_cantus_id = Chant.objects.create(
            cantus_id=chant.cantus_id, source=chant.source
        )
        concordances = chant.related_chants_by_cantus_id()
        self.assertIn(chant_with_same_cantus_id, concordances)

    def test_display_name(self):
        chant = Chant.objects.first()
        display_name = chant.display_name
        name_str = chant.__str__()
        self.assertEqual(display_name, name_str)

    def test_absolute_url(self):
        chant = Chant.objects.first()
        absolute_url = reverse("chant-detail", args=[str(chant.id)])
        self.assertEqual(chant.get_absolute_url(), absolute_url)

    def test_chant_and_sequence_have_same_fields(self):
        chant_fields = Chant.get_fields_and_properties()
        seq_fields = Sequence.get_fields_and_properties()
        self.assertEqual(chant_fields, seq_fields)

    def test_get_next_chant__same_folio_next_sequence_number(self):
        source = make_fake_source()
        current_folio = "001"
        chant1 = make_fake_chant(
            source=source,
            folio=current_folio,
            c_sequence=1,
        )
        chant2 = make_fake_chant(
            source=source,
            folio=current_folio,
            c_sequence=2,
        )
        self.assertEqual(chant1.get_next_chant(), chant2)

    def test_get_next_chant__recto_to_verso(self):
        source = make_fake_source()
        current_folio = "001r"
        next_folio = "001v"
        chant1 = make_fake_chant(
            source=source,
            folio=current_folio,
            c_sequence=1,
        )
        chant2 = make_fake_chant(
            source=source,
            folio=next_folio,
            c_sequence=1,
        )
        self.assertEqual(chant1.get_next_chant(), chant2)

    def test_get_next_chant__verso_to_recto(self):
        source2 = make_fake_source()
        current_folio = "555v"
        next_folio = "556r"
        chant1 = make_fake_chant(
            source=source2,
            folio=current_folio,
            c_sequence=1,
        )
        chant2 = make_fake_chant(
            source=source2,
            folio=next_folio,
            c_sequence=1,
        )
        self.assertEqual(chant1.get_next_chant(), chant2)

    def test_get_next_chant__one_numbered_page_to_the_next(self):
        source = make_fake_source()
        current_folio = "004"
        next_folio = "005"
        end_of_page_chant = make_fake_chant(
            source=source,
            folio=current_folio,
            c_sequence=2,
        )
        beginning_of_next_page_chant = make_fake_chant(
            source=source,
            folio=next_folio,
            c_sequence=1,
        )
        self.assertEqual(
            end_of_page_chant.get_next_chant(), beginning_of_next_page_chant
        )

    def test_get_next_chant__last_chant_in_manuscript(self):
        source = make_fake_source()
        last_folio_in_ms = "999r"
        last_chant_in_ms = make_fake_chant(
            source=source,
            folio=last_folio_in_ms,
            c_sequence=98,
        )
        self.assertIsNone(last_chant_in_ms.get_next_chant())

    def test_get_next_chant__collision(self):
        # if there are multiple chants with the same source, folio and c_sequence,
        # someone has messed up their data entry, and we should set next_chant to None
        source = make_fake_source()
        current_folio = "444"
        chant1 = make_fake_chant(
            source=source,
            folio=current_folio,
            c_sequence=1,
        )
        chant2a = make_fake_chant(
            source=source,
            folio=current_folio,
            c_sequence=2,
        )
        chant2b = make_fake_chant(
            source=source,
            folio=current_folio,
            c_sequence=2,
        )
        self.assertIsNone(chant1.get_next_chant())

    def test_get_next_chant__lacuna(self):
        # if pages from a manuscript have been lost, the lacuna (gap) is often
        # assigned to the previous folio and given a c_sequence of 99.
        source = make_fake_source()
        first_folio = "500v"
        second_folio = "501r"
        chant1 = make_fake_chant(
            source=source,
            folio=first_folio,
            c_sequence=51,
        )
        lacuna = make_fake_chant(
            source=source,
            folio=first_folio,
            c_sequence=99,
            manuscript_full_text_std_spelling="LACUNA",
        )
        chant3 = make_fake_chant(source=source, folio=second_folio, c_sequence=1)
        self.assertEqual(chant1.get_next_chant(), lacuna)
        self.assertEqual(lacuna.get_next_chant(), chant3)


class FeastModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_fake_feast()

    def test_object_name(self):
        feast = Feast.objects.first()
        self.assertEqual(str(feast), feast.name)

    def test_date_constraints(self):
        def create_fake_feast(month, day):
            f = Feast.objects.create(name="fakeFeast", month=month, day=day)

        self.assertRaises(ValidationError, create_fake_feast, month=13, day=1)
        self.assertRaises(ValidationError, create_fake_feast, month=0, day=1)
        self.assertRaises(ValidationError, create_fake_feast, month=-1, day=1)
        self.assertRaises(ValidationError, create_fake_feast, month=1, day=32)
        self.assertRaises(ValidationError, create_fake_feast, month=1, day=0)
        self.assertRaises(ValidationError, create_fake_feast, month=1, day=-1)

    def test_display_name(self):
        feast = Feast.objects.first()
        display_name = feast.display_name
        name_str = feast.__str__()
        self.assertEqual(display_name, name_str)

    def test_absolute_url(self):
        feast = Feast.objects.first()
        absolute_url = reverse("feast-detail", args=[str(feast.id)])
        self.assertEqual(feast.get_absolute_url(), absolute_url)

    def test_update_prefix_field_signal(self):
        feast = make_fake_feast()
        feast_code = "12345678"
        expected_prefix = feast_code[:2]
        feast.feast_code = feast_code
        feast.save()
        feast.refresh_from_db()
        self.assertEqual(feast.feast_code, feast_code)
        self.assertEqual(feast.prefix, expected_prefix)

        feast.feast_code = None
        feast.save()
        feast.refresh_from_db()
        self.assertIs(feast.feast_code, None)
        self.assertEqual(feast.prefix, "")

        feast.feast_code = ""
        feast.save()
        feast.refresh_from_db()
        self.assertIs(feast.feast_code, "")
        self.assertEqual(feast.prefix, "")


class GenreModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_fake_genre()

    def test_string_representation(self):
        genre = Genre.objects.first()
        self.assertEqual(str(genre), f"[{genre.name}] {genre.description}")

    def test_display_name(self):
        genre = Genre.objects.first()
        display_name = genre.display_name
        name_str = genre.__str__()
        self.assertEqual(display_name, name_str)

    def test_absolute_url(self):
        genre = Genre.objects.first()
        absolute_url = reverse("genre-detail", args=[str(genre.id)])
        self.assertEqual(genre.get_absolute_url(), absolute_url)


class OfficeModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_fake_office()

    def test_object_string_representation(self):
        office = Office.objects.first()
        self.assertEqual(str(office), f"[{office.name}] {office.description}")

    def test_display_name(self):
        office = Office.objects.first()
        display_name = office.display_name
        name_str = office.__str__()
        self.assertEqual(display_name, name_str)

    def test_absolute_url(self):
        office = Office.objects.first()
        absolute_url = reverse("office-detail", args=[str(office.id)])
        self.assertEqual(office.get_absolute_url(), absolute_url)


class SequenceModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_fake_sequence()

    def test_display_name(self):
        sequence = Sequence.objects.first()
        display_name = sequence.display_name
        name_str = sequence.__str__()
        self.assertEqual(display_name, name_str)

    def test_absolute_url(self):
        sequence = Sequence.objects.first()
        absolute_url = reverse("sequence-detail", args=[str(sequence.id)])
        self.assertEqual(sequence.get_absolute_url(), absolute_url)

    def test_chant_and_sequence_have_same_fields(self):
        chant_fields = Chant.get_fields_and_properties()
        seq_fields = Sequence.get_fields_and_properties()
        self.assertEqual(chant_fields, seq_fields)


class SourceModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_fake_source()

    def test_number_of_chants(self):
        source = Source.objects.first()
        chant = Chant.objects.create(source=source)
        sequence = Sequence.objects.create(source=source)
        self.assertIn(chant, source.chant_set.all())
        self.assertIn(sequence, source.sequence_set.all())
        self.assertEqual(source.number_of_chants, 2)

    def test_number_of_melodies(self):
        source = Source.objects.first()
        chant_w_melody = Chant.objects.create(source=source, volpiano="1-a-b-c")
        chant = Chant.objects.create(source=source)
        self.assertEqual(source.number_of_melodies, 1)

    def test_display_name(self):
        source = Source.objects.first()
        display_name = source.display_name
        name_str = source.__str__()
        self.assertEqual(display_name, name_str)

    def test_absolute_url(self):
        source = Source.objects.first()
        absolute_url = reverse("source-detail", args=[str(source.id)])
        self.assertEqual(source.get_absolute_url(), absolute_url)


class ChantSequenceSyncTest(TestCase):
    def test_chant_sequence_sync(self):
        # for each of the models:
        # retrieve all fields of that model
        # go through all of the fields and create a list of tuples of the following format:
        # [
        #    ("field name", "field type"),
        #    ("field name", "field type"), ...
        # ]

        # if the two models are defined such that
        # they specify the same fields (with the same name and type) in the same order,
        # we assert true

        chant_field_names = [
            (f.name, f.get_internal_type()) for f in Chant._meta.get_fields()
        ]
        sequence_field_names = [
            (f.name, f.get_internal_type()) for f in Sequence._meta.get_fields()
        ]
        self.assertEqual(chant_field_names, sequence_field_names)
