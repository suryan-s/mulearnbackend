from django.db.models import Count
from rest_framework.views import APIView

from db.task import InterestGroup
from utils.permission import CustomizePermission
from utils.permission import JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DiscordWebhooks
from .dash_ig_serializer import (
    InterestGroupSerializer,
    InterestGroupCreateUpdateSerializer,
)


class InterestGroupAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        ig_queryset = (
            InterestGroup.objects.select_related("created_by", "updated_by")
            .prefetch_related("user_ig_link_ig").annotate(members=Count("user_ig_link_ig"))
            .all()
        )
        paginated_queryset = CommonUtils.get_paginated_queryset(
            ig_queryset,
            request,
            [
                "name",
                "created_by__first_name",
                "created_by__last_name",
                "updated_by__first_name",
                "updated_by__last_name",
            ],
            {
                "name": "name",
                "members": "members",
                "updated_on": "updated_at",
                "updated_by": "updated_by__first_name",
                "created_on": "created_at",
                "created_by": "created_by__first_name",
            },
        )

        ig_serializer_data = InterestGroupSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse().paginated_response(
            data=ig_serializer_data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        request_data = request.data

        request_data["created_by"] = request_data["updated_by"] = user_id

        serializer = InterestGroupCreateUpdateSerializer(
            data=request_data,
        )

        if serializer.is_valid():
            serializer.save()

            DiscordWebhooks.general_updates(
                WebHookCategory.INTEREST_GROUP.value,
                WebHookActions.CREATE.value,
                request_data.get("name"),
            )

            return CustomResponse(
                response={"interestGroup": serializer.data}
            ).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        ig = InterestGroup.objects.get(id=pk)

        ig_old_name = ig.name

        request_data = request.data
        request_data["updated_by"] = user_id

        serializer = InterestGroupCreateUpdateSerializer(
            data=request_data, instance=ig, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            ig_new_name = ig.name

            DiscordWebhooks.general_updates(
                WebHookCategory.INTEREST_GROUP.value,
                WebHookActions.EDIT.value,
                ig_new_name,
                ig_old_name,
            )
            return CustomResponse(
                response={"interestGroup": serializer.data}
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, pk):
        ig = InterestGroup.objects.filter(id=pk).first()

        if ig is None:
            return CustomResponse(general_message="invalid ig").get_success_response()

        ig.delete()

        DiscordWebhooks.general_updates(
            WebHookCategory.INTEREST_GROUP.value,
            WebHookActions.DELETE.value,
            ig.name,
        )
        return CustomResponse(
            general_message="ig deleted successfully"
        ).get_success_response()


class InterestGroupCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        ig_serializer = (
            InterestGroup.objects.select_related("created_by", "updated_by")
            .prefetch_related("user_ig_link_ig").annotate(members=Count("user_ig_link_ig"))
            .all()
        )

        ig_serializer_data = InterestGroupSerializer(ig_serializer, many=True).data

        return CommonUtils.generate_csv(ig_serializer_data, "Interest Group")


class InterestGroupGetAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, pk):
        ig_data = InterestGroup.objects.filter(id=pk).first()

        if not ig_data:
            return CustomResponse(
                general_message="Interest Group Does Not Exist"
            ).get_failure_response()

        serializer = InterestGroupSerializer(ig_data, many=False)

        return CustomResponse(
            response={"interestGroup": serializer.data}
        ).get_success_response()


class InterestGroupListApi(APIView):
    def get(self, request):
        ig = InterestGroup.objects.all()

        serializer = InterestGroupSerializer(ig, many=True)

        return CustomResponse(
            response={"interestGroup": serializer.data}
        ).get_success_response()
