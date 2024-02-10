from datetime import datetime

from django.db.models import QuerySet, F, Count, Value
from django.db.models.functions import Coalesce
from rest_framework import viewsets

from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Order

from rest_framework.pagination import PageNumberPagination

from cinema.serializers import (
    GenreSerializer,
    ActorSerializer,
    CinemaHallSerializer,
    MovieSerializer,
    MovieSessionSerializer,
    MovieSessionListSerializer,
    MovieDetailSerializer,
    MovieSessionDetailSerializer,
    MovieListSerializer,
    OrderSerializer,
    OrderListSerializer,
)


class ParamsTo:
    @staticmethod
    def _params_to_ints(params):
        return [int(param) for param in params.split(",")]


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class CinemaHallViewSet(viewsets.ModelViewSet):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer


class MovieViewSet(ParamsTo, viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer

    def get_queryset(self):
        queryset = self.queryset

        genres = self.request.query_params.get("genres")
        if genres:
            genres_ids = self._params_to_ints(genres)
            queryset = queryset.filter(genres__id__in=genres_ids)

        actors = self.request.query_params.get("actors")
        if actors:
            actors_ids = self._params_to_ints(actors)
            queryset = queryset.filter(actors__id__in=actors_ids)

        title = self.request.query_params.get("title")
        if title:
            queryset = queryset.filter(title__icontains=title)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer

        if self.action == "retrieve":
            return MovieDetailSerializer

        return MovieSerializer


class MovieSessionViewSet(ParamsTo, viewsets.ModelViewSet):
    queryset = MovieSession.objects.all()
    serializer_class = MovieSessionSerializer

    def get_queryset(self) -> QuerySet[MovieSession]:
        queryset = self.queryset
        if self.action == "list":
            date = self.request.query_params.get("date")
            movie = self.request.query_params.get("movie")
            if date:
                date = datetime.strptime(date, "%Y-%m-%d").date()
                queryset = queryset.filter(show_time__date=date)
            queryset = (
                queryset
                .select_related("cinema_hall", "movie")
                .annotate(
                    tickets_available=Coalesce(
                        F("cinema_hall__rows")
                        * F("cinema_hall__seats_in_row")
                        - Count("tickets"),
                        Value(0)
                    )
                )
            )
            if movie:
                queryset = queryset.filter(movie__id=int(movie))

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return MovieSessionListSerializer

        if self.action == "retrieve":
            return MovieSessionDetailSerializer

        return MovieSessionSerializer


class OrderPagination(PageNumberPagination):
    page_size = 1
    page_size_query_param = "page_size"
    max_page_size = 100


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        if self.action == "list":
            queryset = queryset.prefetch_related("tickets__movie_session")
            # queryset = queryset

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
