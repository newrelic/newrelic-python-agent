from django.db import migrations, models
import wagtail.fields
from wagtail.models import Page
import django.db.models.deletion
import wagtail.contrib.routable_page.models


def create_homepage(apps, schema_editor):
    # Get models
    ContentType = apps.get_model("contenttypes.ContentType")
    Page = apps.get_model("wagtailcore.Page")
    Site = apps.get_model("wagtailcore.Site")
    HomePage = apps.get_model("dummy_app.HomePage")

    # Delete the default homepage
    # If migration is run multiple times, it may have already been deleted
    Page.objects.filter(id=2).delete()

    # Create content type for homepage model
    homepage_content_type, __ = ContentType.objects.get_or_create(
        model="homepage", app_label="dummy_app"
    )

    # Create a new homepage
    homepage = HomePage.objects.create(
        title="Home",
        draft_title="Home",
        slug="home",
        content_type=homepage_content_type,
        path="00010001",
        depth=2,
        numchild=0,
        url_path="/home/",
    )

    # Create a site with the new homepage set as the root
    Site.objects.create(hostname="localhost", root_page=homepage, is_default_site=True)

def remove_homepage(apps, schema_editor):
    # Get models
    ContentType = apps.get_model("contenttypes.ContentType")
    HomePage = apps.get_model("dummy_app.HomePage")

    # Delete the default homepage
    # Page and Site objects CASCADE
    HomePage.objects.filter(slug="home", depth=2).delete()

    # Delete content type for homepage model
    ContentType.objects.filter(model="homepage", app_label="dummy_app").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0040_page_draft_title"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.Page",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
        migrations.RunPython(create_homepage, remove_homepage),
        migrations.AddField(
            model_name='homepage',
            name='body',
            field=wagtail.fields.RichTextField(blank=True),
        ),
        migrations.CreateModel(
            name='RoutablePage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
            ],
            options={
                'verbose_name': 'Routable page',
            },
            bases=(wagtail.contrib.routable_page.models.RoutablePage,),
        ),
        migrations.AddField(
            model_name='routablepage',
            name='body',
            field=wagtail.fields.RichTextField(blank=True),
        ),
    ]
