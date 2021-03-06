

from djangae.environment import task_or_admin_only
from djangae.test import TestCase
from djangae.contrib import sleuth
from django.http import HttpResponse


class TaskOrAdminOnlyTestCase(TestCase):
    """ Tests for the @task_or_admin_only decorator. """

    def test_403_if_not_task_or_admin(self):
        # If we are neither in a task or logged in as an admin, we expect a 403 response

        @task_or_admin_only
        def view(request):
            return HttpResponse("Hello")

        response = view(None)
        self.assertEqual(response.status_code, 403)

    def test_allowed_if_in_task(self):
        """ If we're in an App Engine task then it should allow the request through. """

        @task_or_admin_only
        def view(request):
            return HttpResponse("Hello")

        with sleuth.fake("djangae.environment.is_in_task", True):
            response = view(None)
        self.assertEqual(response.status_code, 200)

    def test_allowed_if_in_cron(self):
        """ If the view is being called by the GAE cron, then it should allow the request through. """

        @task_or_admin_only
        def view(request):
            return HttpResponse("Hello")

        with sleuth.fake("djangae.environment.is_in_cron", True):
            response = view(None)
        self.assertEqual(response.status_code, 200)

    def test_allowed_if_admin_user(self):
        """ If we're logged in as an admin of the GAE application then we should allow through. """

        @task_or_admin_only
        def view(request):
            return HttpResponse("Hello")

        with sleuth.fake("google.appengine.api.users.is_current_user_admin", True):
            response = view(None)
        self.assertEqual(response.status_code, 200)
