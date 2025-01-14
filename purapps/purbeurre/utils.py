#!/usr/bin/env python
"""DatabaseInstaller module."""

import re
import requests
from typing import List, Any
from purapps.purbeurre.models import Product, Nutriscore, Category


class Downloader:
    """Download and extract."""

    def __init__(self, nb_page):
        """Init."""
        self.url = "https://fr.openfoodfacts.org/cgi/search.pl?"
        self.payload = {
            "json": 1,
            "action": "process",
            "lang": "fr",
            "page_size": 1000,
            "page": nb_page,
        }
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }

    def extract_data(self):
        """Extract data from API."""
        try:
            r = requests.get(self.url, headers=self.headers, params=self.payload)
            self.result = r.json()
            return self.result["products"]
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)


class Insert:
    """Fill the database."""

    def __init__(self, cleaned_data):
        """Init."""
        self.cleaned_data = cleaned_data

    def insert_data(self):
        """Insert data into DB."""
        if self.cleaned_data:
            for product in self.cleaned_data:
                if product:
                    try:
                        Nutriscore.objects.get(type=product["nutriscore_grade"])
                    except Nutriscore.DoesNotExist:
                        Nutriscore.objects.create(type=product["nutriscore_grade"])

                    try:
                        Product.objects.get(name=product["product_name_fr"])
                    except Product.DoesNotExist:

                        last_nut = Nutriscore.objects.filter(
                            type=product["nutriscore_grade"]
                        ).values("id")

                        Product.objects.create(
                            name=product["product_name_fr"],
                            url=product["url"],
                            brand=product["brands"],
                            stores=product["stores"],
                            nutriscore_id=last_nut,
                        )

                        for category in product["categories"].split(","):
                            categorie = category.strip()
                            try:
                                Category.objects.get(name=categorie)
                            except Category.DoesNotExist:

                                Category.objects.create(name=categorie)

                            prod = Product.objects.get(name=product["product_name_fr"])

                            category = Category.objects.filter(name=categorie).values(
                                "id"
                            )[0]

                            prod.categories.add(category.get("id"))


class Cleaner:
    """Clean all data."""

    validators: List[Any] = []
    normalizers: List[Any] = []

    def is_valid(self, data):
        """Verify if the key has a value."""
        for validator in self.validators:
            if not validator(data):
                return False
        return True

    def normalize(self, data):
        """Normalize some entries."""
        for normalizer in self.normalizers:
            data = normalizer(data)
        return data

    def clean(self, collection):
        """Return a data list if is_valid is True."""
        return [self.normalize(data) for data in collection if self.is_valid(data)]


def require_product_name_fr_not_empty(data):
    """Verify if product_name_fr is not empty."""
    return True if data.get("product_name_fr") else False


def require_stores_not_empty(data):
    """Verify if stores is not empty."""
    return True if data.get("stores") else False


def require_nutriscore_grade_not_empty(data):
    """Verify if nutriscore_grade is not empty."""
    return True if data.get("nutriscore_grade") else False


def require_lang_equal_to_fr(data):
    """Verify if lang is equal to fr."""
    return True if data.get("lang") == "fr" else False


def require_categories_lc_equal_to_fr(data):
    """Verify if categories_lc is equal to fr."""
    return True if data.get("categories_lc") == "fr" else False


def require_categories_without_lot_of_dashes(data):
    """Ignore categories with lot of tirets."""
    item = re.search(r"(\w+\-){1,}", data.get("categories"))
    return False if item else True


def normalize_product_without_cariage_return(data):
    """Delete cariage return."""
    if "\n" in data.get("product_name_fr"):
        return data.update(
            product_name_fr=data.get("product_name_fr").replace("\n", " ")
        )
    return data


def normalize_categories_without_suffix_and_bad_datas(data):
    """Delete expr like -> en: and fr: with all that comes after."""
    if data:
        item = re.search(r"\,\s{0,}\w{2}:", data.get("categories"))
        if item:
            return data.update(categories=data.get("categories")[: item.start()])
        return data


class OffCleaner(Cleaner):
    """State."""

    validators = [
        require_product_name_fr_not_empty,
        require_stores_not_empty,
        require_nutriscore_grade_not_empty,
        require_lang_equal_to_fr,
        require_categories_lc_equal_to_fr,
        require_categories_without_lot_of_dashes,
    ]

    normalizers = [
        normalize_product_without_cariage_return,
        normalize_categories_without_suffix_and_bad_datas,
    ]
