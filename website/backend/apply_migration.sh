#!/bin/bash
export PGPASSWORD='postgres'
psql -h localhost -U postgres -d your_donor -f migrations/add_medical_certificate_fields.sql
echo "Миграция применена!"
