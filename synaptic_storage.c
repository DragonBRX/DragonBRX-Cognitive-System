#include "synaptic_storage.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <jansson.h>
#include <time.h>

#define MAX_MEMORY_ENTRIES 1000 // Limite para o número de entradas de memória
#define INITIAL_STRENGTH 1.0    // Força sináptica inicial
#define DECAY_FACTOR 0.01       // Fator de decaimento por unidade de tempo (ex: por segundo)

static SynapticEntry* g_synaptic_entries = NULL;
static size_t g_current_entries = 0;
static size_t g_max_entries = 0;
static size_t g_embedding_dim = 0;

// Função auxiliar para calcular a similaridade de cosseno
static float cosine_similarity(const float* vec1, const float* vec2, size_t dim) {
    float dot_product = 0.0;
    float norm_vec1 = 0.0;
    float norm_vec2 = 0.0;

    for (size_t i = 0; i < dim; ++i) {
        dot_product += vec1[i] * vec2[i];
        norm_vec1 += vec1[i] * vec1[i];
        norm_vec2 += vec2[i] * vec2[i];
    }

    if (norm_vec1 == 0.0 || norm_vec2 == 0.0) {
        return 0.0; // Evitar divisão por zero
    }

    return dot_product / (sqrt(norm_vec1) * sqrt(norm_vec2));
}

void ss_init(size_t max_entries, size_t embedding_dim) {
    if (g_synaptic_entries != NULL) {
        ss_cleanup(); // Limpa se já estiver inicializado
    }

    g_max_entries = max_entries;
    g_embedding_dim = embedding_dim;
    g_current_entries = 0;

    g_synaptic_entries = (SynapticEntry*)malloc(g_max_entries * sizeof(SynapticEntry));
    if (g_synaptic_entries == NULL) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para entradas sinápticas."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return;
    }
    json_t *response = json_object();
    json_object_set_new(response, "status", json_string("success"));
    json_object_set_new(response, "message", json_string("Módulo de Armazenamento Sináptico inicializado."));
    json_object_set_new(response, "max_entries", json_integer(g_max_entries));
    json_object_set_new(response, "embedding_dim", json_integer(g_embedding_dim));
    fprintf(stdout, "%s\n", json_dumps(response, 0));
    json_decref(response);
}

int ss_add_entry(const char* id, const float* embedding_data, size_t embedding_dim, const char* content) {
    if (g_synaptic_entries == NULL || g_current_entries >= g_max_entries || embedding_dim != g_embedding_dim) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Módulo não inicializado, cheio ou dimensão de embedding incorreta."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return -1;
    }

    SynapticEntry* new_entry = &g_synaptic_entries[g_current_entries];

    new_entry->id = strdup(id);
    if (new_entry->id == NULL) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para ID."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return -1;
    }

    new_entry->embedding.data = (float*)malloc(embedding_dim * sizeof(float));
    if (new_entry->embedding.data == NULL) {
        free(new_entry->id);
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para embedding."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return -1;
    }
    memcpy(new_entry->embedding.data, embedding_data, embedding_dim * sizeof(float));
    new_entry->embedding.dim = embedding_dim;

    new_entry->content = strdup(content);
    if (new_entry->content == NULL) {
        free(new_entry->id);
        free(new_entry->embedding.data);
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para conteúdo."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return -1;
    }
    
    new_entry->last_accessed = time(NULL); // Inicializa com o tempo atual
    new_entry->strength = INITIAL_STRENGTH; // Força inicial

    g_current_entries++;
    json_t *response = json_object();
    json_object_set_new(response, "status", json_string("success"));
    json_object_set_new(response, "message", json_string("Entrada sináptica adicionada."));
    json_object_set_new(response, "id", json_string(id));
    json_object_set_new(response, "total_entries", json_integer(g_current_entries));
    fprintf(stdout, "%s\n", json_dumps(response, 0));
    json_decref(response);
    return 0;
}

void ss_update_plasticity(const char* id) {
    for (size_t i = 0; i < g_current_entries; ++i) {
        if (strcmp(g_synaptic_entries[i].id, id) == 0) {
            g_synaptic_entries[i].last_accessed = time(NULL);
            g_synaptic_entries[i].strength += 0.1; // Aumenta a força ao ser acessada
            if (g_synaptic_entries[i].strength > 1.0) g_synaptic_entries[i].strength = 1.0; // Limite superior
            return;
        }
    }
}

void ss_apply_decay(float decay_rate, time_t current_time) {
    for (size_t i = 0; i < g_current_entries; ++i) {
        double time_diff = difftime(current_time, g_synaptic_entries[i].last_accessed);
        // Aplica decaimento baseado no tempo desde o último acesso
        g_synaptic_entries[i].strength -= decay_rate * time_diff;
        if (g_synaptic_entries[i].strength < 0.0) g_synaptic_entries[i].strength = 0.0; // Limite inferior
    }
}

SynapticEntry** ss_search(const float* query_embedding_data, size_t query_dim, int n_results, int* num_results) {
    if (g_synaptic_entries == NULL || query_dim != g_embedding_dim) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Módulo não inicializado ou dimensão de query incorreta."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        *num_results = 0;
        return NULL;
    }

    typedef struct {
        SynapticEntry* entry;
        float similarity;
    } SearchResult;

    SearchResult* temp_results = (SearchResult*)malloc(g_current_entries * sizeof(SearchResult));
    if (temp_results == NULL) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para resultados temporários."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        *num_results = 0;
        return NULL;
    }

    for (size_t i = 0; i < g_current_entries; ++i) {
        temp_results[i].entry = &g_synaptic_entries[i];
        temp_results[i].similarity = cosine_similarity(query_embedding_data, g_synaptic_entries[i].embedding.data, g_embedding_dim);
        // Pondera a similaridade pela força sináptica
        temp_results[i].similarity *= g_synaptic_entries[i].strength;
    }

    // Ordenar os resultados por similaridade (do maior para o menor)
    for (size_t i = 0; i < g_current_entries; ++i) {
        for (size_t j = i + 1; j < g_current_entries; ++j) {
            if (temp_results[i].similarity < temp_results[j].similarity) {
                SearchResult temp = temp_results[i];
                temp_results[i] = temp_results[j];
                temp_results[j] = temp;
            }
        }
    }

    *num_results = (g_current_entries < n_results) ? g_current_entries : n_results;
    SynapticEntry** final_results = (SynapticEntry**)malloc(*num_results * sizeof(SynapticEntry*));
    if (final_results == NULL) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para resultados finais."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        free(temp_results);
        *num_results = 0;
        return NULL;
    }

    for (int i = 0; i < *num_results; ++i) {
        final_results[i] = temp_results[i].entry;
        // Atualiza a plasticidade da entrada acessada
        ss_update_plasticity(temp_results[i].entry->id);
    }

    free(temp_results);
    return final_results;
}

void ss_free_entry(SynapticEntry* entry) {
    if (entry) {
        free(entry->id);
        free(entry->embedding.data);
        free(entry->content);
    }
}

void ss_free_search_results(SynapticEntry** results) {
    // Note: As entradas retornadas por ss_search apontam para a memória global g_synaptic_entries.
    // Apenas o array de ponteiros precisa ser liberado, não as entradas em si.
    free(results);
}

void ss_cleanup() {
    if (g_synaptic_entries != NULL) {
        for (size_t i = 0; i < g_current_entries; ++i) {
            ss_free_entry(&g_synaptic_entries[i]);
        }
        free(g_synaptic_entries);
        g_synaptic_entries = NULL;
    }
    g_current_entries = 0;
    g_max_entries = 0;
    g_embedding_dim = 0;
    json_t *response = json_object();
    json_object_set_new(response, "status", json_string("success"));
    json_object_set_new(response, "message", json_string("Módulo de Armazenamento Sináptico limpo."));
    fprintf(stdout, "%s\n", json_dumps(response, 0));
    json_decref(response);
}

int main(int argc, char *argv[]) {
    char buffer[4096];
    while (fgets(buffer, sizeof(buffer), stdin) != NULL) {
        json_error_t error;
        json_t *root = json_loads(buffer, 0, &error);

        if (!root) {
            json_t *response = json_object();
            json_object_set_new(response, "status", json_string("error"));
            json_object_set_new(response, "message", json_string(error.text));
            fprintf(stdout, "%s\n", json_dumps(response, 0));
            json_decref(response);
            fflush(stdout);
            continue;
        }

        json_t *command_json = json_object_get(root, "command");
        if (!json_is_string(command_json)) {
            json_t *response = json_object();
            json_object_set_new(response, "status", json_string("error"));
            json_object_set_new(response, "message", json_string("Comando JSON inválido."));
            fprintf(stdout, "%s\n", json_dumps(response, 0));
            json_decref(response);
            json_decref(root);
            fflush(stdout);
            continue;
        }
        const char *command = json_string_value(command_json);

        if (strcmp(command, "init") == 0) {
            json_t *max_entries_json = json_object_get(root, "max_entries");
            json_t *embedding_dim_json = json_object_get(root, "embedding_dim");
            size_t max_entries = json_is_integer(max_entries_json) ? json_integer_value(max_entries_json) : 100;
            size_t embedding_dim = json_is_integer(embedding_dim_json) ? json_integer_value(embedding_dim_json) : 384;
            ss_init(max_entries, embedding_dim);
        } else if (strcmp(command, "add") == 0) {
            json_t *id_json = json_object_get(root, "id");
            json_t *content_json = json_object_get(root, "content");
            json_t *embedding_json = json_object_get(root, "embedding");

            if (!json_is_string(id_json) || !json_is_string(content_json) || !json_is_array(embedding_json)) {
                json_t *response = json_object();
                json_object_set_new(response, "status", json_string("error"));
                json_object_set_new(response, "message", json_string("Dados de entrada inválidos para o comando add."));
                fprintf(stdout, "%s\n", json_dumps(response, 0));
                json_decref(response);
                json_decref(root);
                fflush(stdout);
                continue;
            }

            const char *id = json_string_value(id_json);
            const char *content = json_string_value(content_json);
            size_t embedding_dim_received = json_array_size(embedding_json);
            float *embedding_data = (float*)malloc(embedding_dim_received * sizeof(float));
            if (!embedding_data) {
                json_t *response = json_object();
                json_object_set_new(response, "status", json_string("error"));
                json_object_set_new(response, "message", json_string("Falha ao alocar memória para embedding data."));
                fprintf(stdout, "%s\n", json_dumps(response, 0));
                json_decref(response);
                json_decref(root);
                fflush(stdout);
                continue;
            }

            for (size_t i = 0; i < embedding_dim_received; ++i) {
                json_t *value = json_array_get(embedding_json, i);
                if (!json_is_number(value)) {
                    free(embedding_data);
                    json_t *response = json_object();
                    json_object_set_new(response, "status", json_string("error"));
                    json_object_set_new(response, "message", json_string("Embedding contém valores não numéricos."));
                    fprintf(stdout, "%s\n", json_dumps(response, 0));
                    json_decref(response);
                    json_decref(root);
                    fflush(stdout);
                    continue;
                }
                embedding_data[i] = (float)json_number_value(value);
            }
            ss_add_entry(id, embedding_data, embedding_dim_received, content);
            free(embedding_data);
        } else if (strcmp(command, "search") == 0) {
            json_t *query_embedding_json = json_object_get(root, "query_embedding");
            json_t *n_results_json = json_object_get(root, "n_results");

            if (!json_is_array(query_embedding_json)) {
                json_t *response = json_object();
                json_object_set_new(response, "status", json_string("error"));
                json_object_set_new(response, "message", json_string("Query embedding inválido."));
                fprintf(stdout, "%s\n", json_dumps(response, 0));
                json_decref(response);
                json_decref(root);
                fflush(stdout);
                continue;
            }

            size_t query_dim = json_array_size(query_embedding_json);
            float *query_embedding_data = (float*)malloc(query_dim * sizeof(float));
            if (!query_embedding_data) {
                json_t *response = json_object();
                json_object_set_new(response, "status", json_string("error"));
                json_object_set_new(response, "message", json_string("Falha ao alocar memória para query embedding data."));
                fprintf(stdout, "%s\n", json_dumps(response, 0));
                json_decref(response);
                json_decref(root);
                fflush(stdout);
                continue;
            }

            for (size_t i = 0; i < query_dim; ++i) {
                json_t *value = json_array_get(query_embedding_json, i);
                if (!json_is_number(value)) {
                    free(query_embedding_data);
                    json_t *response = json_object();
                    json_object_set_new(response, "status", json_string("error"));
                    json_object_set_new(response, "message", json_string("Query embedding contém valores não numéricos."));
                    fprintf(stdout, "%s\n", json_dumps(response, 0));
                    json_decref(response);
                    json_decref(root);
                    fflush(stdout);
                    continue;
                }
                query_embedding_data[i] = (float)json_number_value(value);
            }

            int n_results = json_is_integer(n_results_json) ? json_integer_value(n_results_json) : 3;
            int num_found_results;
            SynapticEntry** results = ss_search(query_embedding_data, query_dim, n_results, &num_found_results);
            
            json_t *response = json_object();
            json_object_set_new(response, "status", json_string("success"));
            json_t *results_array = json_array();
            for (int i = 0; i < num_found_results; ++i) {
                json_t *result_obj = json_object();
                json_object_set_new(result_obj, "id", json_string(results[i]->id));
                json_object_set_new(result_obj, "content", json_string(results[i]->content));
                json_object_set_new(result_obj, "strength", json_real(results[i]->strength)); // Adiciona a força sináptica
                json_array_append_new(results_array, result_obj);
            }
            json_object_set_new(response, "results", results_array);
            fprintf(stdout, "%s\n", json_dumps(response, 0));
            json_decref(response);
            ss_free_search_results(results);
            free(query_embedding_data);
        } else if (strcmp(command, "apply_decay") == 0) {
            json_t *decay_rate_json = json_object_get(root, "decay_rate");
            float decay_rate = json_is_number(decay_rate_json) ? json_number_value(decay_rate_json) : DECAY_FACTOR;
            ss_apply_decay(decay_rate, time(NULL));
            json_t *response = json_object();
            json_object_set_new(response, "status", json_string("success"));
            json_object_set_new(response, "message", json_string("Decaimento sináptico aplicado."));
            fprintf(stdout, "%s\n", json_dumps(response, 0));
            json_decref(response);
        } else if (strcmp(command, "cleanup") == 0) {
            ss_cleanup();
        } else {
            json_t *response = json_object();
            json_object_set_new(response, "status", json_string("error"));
            json_object_set_new(response, "message", json_string("Comando desconhecido ou formato inválido."));
            fprintf(stdout, "%s\n", json_dumps(response, 0));
            json_decref(response);
        }
        json_decref(root);
        fflush(stdout);
    }
    return 0;
}
