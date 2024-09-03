# -*- coding: utf-8 -*-
"""
TheSeedCore KafkaServiceModule

######################################################################################################################################
# This module provides a Kafka service that facilitates the management of Kafka clusters,
# producers, consumers, and topics. It is designed to support robust communication and data
# streaming through Kafka, with features for monitoring and controlling Kafka resources.

# Main functionalities:
# 1. Manage Kafka clusters, including adding and updating configurations.
# 2. Create and manage Kafka producers and consumers for message streaming.
# 3. Create, configure, and monitor Kafka topics.
# 4. Send and receive messages with serialization support using Kafka.
# 5. Monitor cluster health, manage offsets, and handle Kafka consumer groups.

# Main components:
# 1. KafkaService - Manages the lifecycle and interactions with Kafka clusters, producers, consumers, and topics.
# 2. defaultLogger - Provides custom logging functionality for Kafka service operations.

# Design thoughts:
# 1. Centralized Kafka management:
#    a. The module is designed to manage multiple Kafka clusters and their associated resources
#       (producers, consumers, topics) from a single service instance.
#    b. It allows for easy scaling and management of Kafka resources across different environments.
#
# 2. Resilience and error handling:
#    a. Extensive error handling is implemented across all Kafka operations, ensuring that issues
#       are logged and do not cause the system to fail unexpectedly.
#    b. Callback mechanisms are provided for successful and failed message deliveries, allowing for
#       more granular control over the message lifecycle.
#
# 3. Monitoring and configuration:
#    a. The service includes tools for monitoring Kafka clusters, including metrics collection and
#       health checks, to ensure that the Kafka environment is operating optimally.
#    b. Configuration management is made easy with methods to update and monitor cluster configurations,
#       as well as alter topic settings dynamically.
#
# 4. Scalability and performance:
#    a. The service supports the creation of multiple producers and consumers within a Kafka cluster,
#       allowing for high-throughput message streaming.
#    b. The service is optimized for performance with the use of asynchronous messaging and efficient
#       resource management.
#
# 5. Integration and extensibility:
#    a. The service is designed to integrate easily with other components and services, providing
#       a flexible API for interacting with Kafka resources.
#    b. The module can be extended to support additional Kafka features or
######################################################################################################################################
"""

from __future__ import annotations

__all__ = [
    "KafkaService",
    "KafkaSupport"
]

import logging
import pickle
import traceback
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from . import _ColoredFormatter

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger

KafkaSupport = False


def defaultLogger(debug_mode: bool = False) -> logging.Logger:
    logger = logging.getLogger(f'TheSeedCore - KafkaService')
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    if debug_mode:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(max(logging.DEBUG, logging.WARNING))

    formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger


try:
    # noinspection PyUnresolvedReferences
    from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient, TopicPartition
    # noinspection PyUnresolvedReferences
    from kafka.admin import NewTopic, ConfigResource, ConfigResourceType
except ImportError:
    class KafkaService:
        INSTANCE: KafkaService = None

        # noinspection PyUnusedLocal
        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            raise ImportError("The kafka-python is not installed. Please install it using 'pip install kafka-python'.")
else:
    KafkaSupport = True


    class KafkaService:
        INSTANCE: KafkaService = None
        _INITIALIZED: bool = False

        def __new__(cls, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False, *args, **kwargs):
            if cls.INSTANCE is None:
                # noinspection PySuperArguments
                cls.INSTANCE = super(KafkaService, cls).__new__(cls)
            return cls.INSTANCE

        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            if not self._INITIALIZED:
                self._Logger = defaultLogger(DebugMode) if Logger is None else Logger
                self._Clusters: Dict[str, Dict[str, Any]] = {}
                KafkaService._INITIALIZED = True

        def addCluster(self, cluster_id: str, admin_configs: Optional[Dict[str, Any]] = None):
            if cluster_id not in self._Clusters:
                self._Clusters[cluster_id] = {
                    "producers": {},
                    "consumers": {},
                    "admin_client": KafkaAdminClient(**admin_configs) if admin_configs else None
                }
                self._Logger.info(f"Cluster {cluster_id} added.")

        def updateClusterConfig(self, cluster_id: str, new_admin_configs: Dict[str, Any]):
            """更新集群配置"""
            if cluster_id in self._Clusters:
                try:
                    self._Clusters[cluster_id]["admin_client"].close()
                    self._Clusters[cluster_id]["admin_client"] = KafkaAdminClient(**new_admin_configs)
                    self._Logger.info(f"Cluster {cluster_id} configuration updated.")
                except Exception as e:
                    self._Logger.error(f"Updating cluster {cluster_id} configuration failed: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Update cluster config failed: Cluster {cluster_id} not found.")

        def monitorCluster(self, cluster_id: str):
            if cluster_id in self._Clusters:
                try:
                    admin_client = self._Clusters[cluster_id]["admin_client"]
                    if admin_client:
                        metrics = admin_client.metrics()
                        self._Logger.info(f"Cluster {cluster_id} metrics: {metrics}")
                        return metrics
                    else:
                        self._Logger.error(f"Monitor cluster failed: No admin client found for cluster {cluster_id}.")
                except Exception as e:
                    self._Logger.error(f"Error during monitoring cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Monitor cluster failed: Cluster {cluster_id} not found.")
            return None

        def createProducer(self, cluster_id: str, client_id: str, **configs):
            if cluster_id in self._Clusters:
                configs["client_id"] = client_id
                producer = KafkaProducer(**configs)
                self._Clusters[cluster_id]["producers"][client_id] = producer
                self._Logger.info(f"Producer created for client_id: {client_id} in cluster {cluster_id}")
            else:
                self._Logger.error(f"Create producer failed: Cluster {cluster_id} not found.")

        def createConsumer(self, cluster_id: str, client_id: str, topics: List[str], **configs):
            if cluster_id in self._Clusters:
                configs["client_id"] = client_id
                consumer = KafkaConsumer(*topics, **configs)
                self._Clusters[cluster_id]["consumers"][client_id] = consumer
                self._Logger.info(f"Consumer created for client_id: {client_id} in cluster {cluster_id}")
            else:
                self._Logger.error(f"Create consumer failed: Cluster {cluster_id} not found.")

        def createTopic(self, cluster_id: str, topic_name: str, num_partitions: int, replication_factor: int, **configs):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        topic = NewTopic(name=topic_name, num_partitions=num_partitions, replication_factor=replication_factor, **configs)
                        admin_client.create_topics([topic])
                        self._Logger.debug(f"Topic {topic_name} created in cluster {cluster_id}.")
                    except Exception as e:
                        self._Logger.error(f"Creating topic {topic_name} in cluster {cluster_id} failed: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Create topic failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"Create topic failed: Cluster {cluster_id} not found.")

        def sendMessage(self, cluster_id: str, client_id: str, topic: str, data: Any):
            if cluster_id in self._Clusters:
                producer = self._Clusters[cluster_id]["producers"].get(client_id)
                if producer:
                    serialized_data = pickle.dumps(data)
                    producer.send(topic, value=serialized_data).add_callback(self.onSendSuccess).add_errback(self.onSendError)
                    self._Logger.info(f"Message sent to topic {topic} by producer {client_id} in cluster {cluster_id}")
                else:
                    self._Logger.error(f"Send message failed: Producer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                self._Logger.error(f"Send message failed: Cluster {cluster_id} not found.")

        def receiveMessage(self, cluster_id: str, client_id: str, msg_callback):
            if cluster_id in self._Clusters:
                consumer = self._Clusters[cluster_id]["consumers"].get(client_id)
                if consumer:
                    for msg in consumer:
                        data = pickle.loads(msg.value)
                        msg_callback(data)
                    self._Logger.info(f"Messages received by consumer {client_id} in cluster {cluster_id}")
                else:
                    self._Logger.error(f"Receive message failed: Consumer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                self._Logger.error(f"Receive message failed: Cluster {cluster_id} not found.")

        def onSendSuccess(self, record_metadata):
            self._Logger.info(f"Message sent successfully: {record_metadata.topic} - {record_metadata.partition} - {record_metadata.offset}")

        def onSendError(self, exception):
            self._Logger.error(f"Error sending message: {exception}")

        def closeSingleProducer(self, cluster_id: str, client_id: str):
            if cluster_id in self._Clusters:
                producer = self._Clusters[cluster_id]["producers"].get(client_id)
                if producer:
                    try:
                        producer.close()
                        del self._Clusters[cluster_id]["producers"][client_id]
                        self._Logger.info(f"Producer {client_id} closed and removed from cluster {cluster_id}.")
                    except Exception as e:
                        self._Logger.error(f"Close producer {client_id} in cluster {cluster_id} failed: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Close producer failed: Producer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                self._Logger.error(f"Close producer failed: Cluster {cluster_id} not found.")

        def closeSingleConsumer(self, cluster_id: str, client_id: str):
            if cluster_id in self._Clusters:
                consumer = self._Clusters[cluster_id]["consumers"].get(client_id)
                if consumer:
                    try:
                        consumer.close()
                        del self._Clusters[cluster_id]["consumers"][client_id]
                        self._Logger.info(f"Consumer {client_id} closed and removed from cluster {cluster_id}.")
                    except Exception as e:
                        self._Logger.error(f"Close consumer {client_id} in cluster {cluster_id} failed: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Close consumer failed: Consumer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                self._Logger.error(f"Close consumer failed: Cluster {cluster_id} not found.")

        def closeAllProducers(self, cluster_id: str):
            if cluster_id in self._Clusters:
                for client_id in list(self._Clusters[cluster_id]["producers"].keys()):
                    self.closeSingleProducer(cluster_id, client_id)
            else:
                self._Logger.error(f"Close all producers failed: Cluster {cluster_id} not found.")

        def closeAllConsumers(self, cluster_id: str):
            if cluster_id in self._Clusters:
                for client_id in list(self._Clusters[cluster_id]["consumers"].keys()):
                    self.closeSingleConsumer(cluster_id, client_id)
            else:
                self._Logger.error(f"Close all consumers failed: Cluster {cluster_id} not found.")

        def closeAllClusters(self):
            for cluster_id in list(self._Clusters.keys()):
                self.closeAllProducers(cluster_id)
                self.closeAllConsumers(cluster_id)
                self._Clusters[cluster_id]["admin_client"].close()
                del self._Clusters[cluster_id]
            self._Logger.info("All clusters closed and removed.")

        def getProducer(self, cluster_id: str, client_id: str):
            if cluster_id in self._Clusters:
                try:
                    return self._Clusters[cluster_id]["producers"][client_id]
                except KeyError:
                    raise ValueError(f"Producer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                raise ValueError(f"Cluster {cluster_id} not found.")

        def getConsumer(self, cluster_id: str, client_id: str):
            if cluster_id in self._Clusters:
                try:
                    return self._Clusters[cluster_id]["consumers"][client_id]
                except KeyError:
                    raise ValueError(f"Consumer with client_id {client_id} not found in cluster {cluster_id}.")
            else:
                raise ValueError(f"Cluster {cluster_id} not found.")

        def listTopics(self, cluster_id: str):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        topics = admin_client.list_topics()
                        self._Logger.info(f"Available topics in cluster {cluster_id}: {topics}")
                        return topics
                    except Exception as e:
                        self._Logger.error(f"Error listing topics in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"List topics failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"List topics failed: Cluster {cluster_id} not found.")
            return []

        def listConsumerGroups(self, cluster_id: str):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        consumer_groups = admin_client.list_consumer_groups()
                        self._Logger.info(f"Consumer groups in cluster {cluster_id}: {consumer_groups}")
                        return consumer_groups
                    except Exception as e:
                        self._Logger.error(f"Error listing consumer groups in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"List consumer groups failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"List consumer groups failed: Cluster {cluster_id} not found.")
            return []

        def describeConsumerGroup(self, cluster_id: str, group_id: str):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        group_description = admin_client.describe_consumer_groups([group_id])
                        self._Logger.info(f"Description for group {group_id} in cluster {cluster_id}: {group_description}")
                        return group_description
                    except Exception as e:
                        self._Logger.error(f"Error describing consumer group {group_id} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Describe consumer group failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"Describe consumer group failed: Cluster {cluster_id} not found.")
            return {}

        def alterTopicConfig(self, cluster_id: str, topic_name: str, config: Dict[str, str]):
            if cluster_id in self._Clusters:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    try:
                        config_resource = ConfigResource(ConfigResourceType.TOPIC, topic_name)
                        config_entries = {k: v for k, v in config.items()}
                        admin_client.alter_configs({config_resource: config_entries})
                        self._Logger.info(f"Config for topic {topic_name} updated in cluster {cluster_id}.")
                    except Exception as e:
                        self._Logger.error(f"Error altering topic config for {topic_name} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
                else:
                    self._Logger.error(f"Alter topic config failed: No admin client found for cluster {cluster_id}.")
            else:
                self._Logger.error(f"Alter topic config failed: Cluster {cluster_id} not found.")

        def getOffsets(self, cluster_id: str, topic_name: str, partition: int):
            if cluster_id in self._Clusters:
                try:
                    consumer = self._Clusters[cluster_id]["consumers"].get("offsets_consumer")
                    if not consumer:
                        consumer = KafkaConsumer(group_id='offsets_consumer', enable_auto_commit=False)
                        self._Clusters[cluster_id]["consumers"]['offsets_consumer'] = consumer
                    tp = TopicPartition(topic_name, partition)
                    offsets = consumer.end_offsets([tp])
                    self._Logger.info(f"Offsets for {topic_name} partition {partition} in cluster {cluster_id}: {offsets[tp]}")
                    return offsets[tp]
                except Exception as e:
                    self._Logger.error(f"Error getting offsets for {topic_name} partition {partition} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Get offsets failed: Cluster {cluster_id} not found.")
            return None

        def setOffsets(self, cluster_id: str, topic_name: str, partition: int, offset: int):
            if cluster_id in self._Clusters:
                try:
                    consumer = self._Clusters[cluster_id]["consumers"].get("offsets_consumer")
                    if not consumer:
                        consumer = KafkaConsumer(group_id='offsets_consumer', enable_auto_commit=False)
                        self._Clusters[cluster_id]["consumers"]['offsets_consumer'] = consumer
                    tp = TopicPartition(topic_name, partition)
                    consumer.seek(tp, offset)
                    self._Logger.info(f"Offset for {topic_name} partition {partition} set to {offset} in cluster {cluster_id}")
                except Exception as e:
                    self._Logger.error(f"Error setting offsets for {topic_name} partition {partition} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Set offsets failed: Cluster {cluster_id} not found.")

        def checkHealth(self, cluster_id: str):
            if cluster_id in self._Clusters:
                try:
                    admin_client = self._Clusters[cluster_id]["admin_client"]
                    if admin_client:
                        brokers = admin_client.describe_cluster().brokers
                        if brokers:
                            self._Logger.info(f"Cluster {cluster_id} health check passed. Brokers: {brokers}")
                            return True
                        else:
                            self._Logger.warning(f"No brokers found in the cluster {cluster_id}.")
                    else:
                        self._Logger.error(f"Check health failed: No admin client found for cluster {cluster_id}.")
                except Exception as e:
                    self._Logger.error(f"Error during health check for cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Check health failed: Cluster {cluster_id} not found.")
            return False
